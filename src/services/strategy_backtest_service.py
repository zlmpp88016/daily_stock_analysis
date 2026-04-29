# -*- coding: utf-8 -*-
"""Service orchestration for strategy backtest runs."""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd

from src.repositories.stock_repo import StockRepository
from src.repositories.strategy_backtest_repo import StrategyBacktestRepository
from src.storage import DatabaseManager, StrategyBacktestRun
from src.strategy_backtest.engine import BacktestConfig, StrategyBacktestEngine
from src.strategy_backtest.indicators import calc_indicators
from src.strategy_backtest.models import (
    StrategyBacktestEquityResponse as StrategyBacktestEquitySchema,
    StrategyBacktestRequest,
    StrategyBacktestRunResponse as StrategyBacktestRunSchema,
    StrategyBacktestTradeResponse as StrategyBacktestTradeSchema,
)
from src.strategy_backtest.rules import evaluate_rules

logger = logging.getLogger(__name__)


class StrategyBacktestService:
    """Service layer for running and querying strategy backtests."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        *,
        fetcher_manager: Optional[Any] = None,
        engine: Optional[StrategyBacktestEngine] = None,
    ):
        self.db = db_manager or DatabaseManager.get_instance()
        self.repo = StrategyBacktestRepository(self.db)
        self.stock_repo = StockRepository(self.db)
        self.fetcher_manager = fetcher_manager
        self.engine = engine or StrategyBacktestEngine()

    def run_backtest(
        self,
        *,
        code: str,
        start_date: date,
        end_date: date,
        initial_cash: float,
        indicators: Any,
        buy_rules: Sequence[str],
        sell_rules: Sequence[str],
        commission_rate: float = 0.0,
        slippage_rate: float = 0.0,
        execution_mode: str = "next_open",
    ) -> Dict[str, Any]:
        """Load historical data from storage, execute one backtest, and persist the result."""
        request = StrategyBacktestRequest(
            code=code,
            start_date=start_date,
            end_date=end_date,
            initial_cash=initial_cash,
            commission_rate=commission_rate,
            slippage_rate=slippage_rate,
            execution_mode=execution_mode,
            indicators=indicators,
            buy_rules=list(buy_rules),
            sell_rules=list(sell_rules),
        )

        market_df = self._load_market_frame_from_storage(
            code=request.code,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        prepared_df = self._prepare_market_frame(
            market_df,
            start_date=request.start_date,
            end_date=request.end_date,
        )

        indicator_config = request.indicators.model_dump(exclude_none=True)
        self._validate_strategy_inputs(
            df=prepared_df,
            indicator_config=indicator_config,
            buy_rules=request.buy_rules,
            sell_rules=request.sell_rules,
        )

        result = self.engine.run(
            prepared_df,
            BacktestConfig(
                initial_cash=request.initial_cash,
                commission_rate=request.commission_rate,
                slippage_rate=request.slippage_rate,
                execution_mode=request.execution_mode,
                indicators=indicator_config,
                buy_rules=request.buy_rules,
                sell_rules=request.sell_rules,
            ),
        )

        run = StrategyBacktestRun(
            code=request.code,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_cash=request.initial_cash,
            commission_rate=request.commission_rate,
            slippage_rate=request.slippage_rate,
            execution_mode=request.execution_mode,
            indicators_json=json.dumps(indicator_config, ensure_ascii=False),
            buy_rules_json=json.dumps(request.buy_rules, ensure_ascii=False),
            sell_rules_json=json.dumps(request.sell_rules, ensure_ascii=False),
            status="completed",
            total_return=result.summary.total_return,
            max_drawdown=result.summary.max_drawdown,
            win_rate=result.summary.win_rate,
            trade_count=result.summary.trade_count,
            avg_holding_days=result.summary.avg_holding_days,
        )

        with self.db.session_scope() as session:
            saved_run = self.repo.save_run(run, session=session)
            self.repo.save_trades(saved_run.id, result.trades, session=session)
            self.repo.save_equity(saved_run.id, result.equity_points, session=session)
            run_data = self._serialize_run(saved_run)

        return run_data

    def get_history(self, *, code: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Return recent persisted strategy backtest runs."""
        rows = self.repo.get_history(code=code, limit=limit)
        return [self._serialize_run(row) for row in rows]

    def get_run_detail(self, run_id: int) -> Optional[Dict[str, Any]]:
        """Return one strategy backtest run with trades and equity curve."""
        data = self.repo.get_run(run_id)
        if data is None:
            return None

        return {
            **self._serialize_run(data["run"]),
            "trades": [self._serialize_trade(row) for row in data["trades"]],
            "equity_curve": [self._serialize_equity(row) for row in data["equity_curve"]],
        }

    def _load_market_frame_from_storage(
        self,
        *,
        code: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        rows = self.stock_repo.get_range(code=code, start_date=start_date, end_date=end_date)
        if not rows:
            raise ValueError(
                f"No historical data found in database for {code} within {start_date} to {end_date}."
            )

        return pd.DataFrame(
            [
                {
                    "date": row.date,
                    "open": row.open,
                    "high": row.high,
                    "low": row.low,
                    "close": row.close,
                    "volume": row.volume,
                    "amount": row.amount,
                    "pct_chg": row.pct_chg,
                }
                for row in rows
            ]
        )

    @staticmethod
    def _prepare_market_frame(df: pd.DataFrame, *, start_date: date, end_date: date) -> pd.DataFrame:
        if df is None or df.empty:
            raise ValueError("No historical data found in database for the requested stock.")

        prepared = df.copy(deep=True)
        required_columns = ("date", "open", "close")
        missing_columns = [column for column in required_columns if column not in prepared.columns]
        if missing_columns:
            raise ValueError(f"Fetched historical data missing required columns: {', '.join(missing_columns)}")

        try:
            prepared["date"] = pd.to_datetime(prepared["date"]).dt.date
        except (TypeError, ValueError) as exc:
            raise ValueError("Fetched historical data contains invalid dates.") from exc

        prepared = prepared[
            (prepared["date"] >= start_date) & (prepared["date"] <= end_date)
        ].sort_values("date").reset_index(drop=True)

        if prepared.empty:
            raise ValueError("No historical data available within the requested date range.")

        return prepared

    @staticmethod
    def _validate_strategy_inputs(
        *,
        df: pd.DataFrame,
        indicator_config: Dict[str, Any],
        buy_rules: Sequence[str],
        sell_rules: Sequence[str],
    ) -> None:
        enriched_df = calc_indicators(df, indicator_config)
        evaluate_rules(enriched_df, list(buy_rules))
        evaluate_rules(enriched_df, list(sell_rules))

    @staticmethod
    def _serialize_run(row: Any) -> Dict[str, Any]:
        data = StrategyBacktestRunSchema.model_validate(row).model_dump(mode="json")
        indicators = data.get("indicators")
        if isinstance(indicators, dict):
            data["indicators"] = {key: value for key, value in indicators.items() if value is not None}
        return data

    @staticmethod
    def _serialize_trade(row: Any) -> Dict[str, Any]:
        return StrategyBacktestTradeSchema.model_validate(row).model_dump(mode="json")

    @staticmethod
    def _serialize_equity(row: Any) -> Dict[str, Any]:
        return StrategyBacktestEquitySchema.model_validate(row).model_dump(mode="json")
