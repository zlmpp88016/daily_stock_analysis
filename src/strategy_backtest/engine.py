from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

import pandas as pd

from src.strategy_backtest.indicators import calc_indicators
from src.strategy_backtest.rules import evaluate_rules


TradeType = Literal["buy", "sell"]
PendingOrder = Literal["buy", "sell"]


@dataclass(frozen=True)
class BacktestConfig:
    """Configuration for a pure daily-bar backtest run."""

    initial_cash: float
    commission_rate: float = 0.0
    slippage_rate: float = 0.0
    execution_mode: str = "next_open"
    indicators: Mapping[str, Any] | Any | None = None
    buy_rules: Sequence[Any] = field(default_factory=tuple)
    sell_rules: Sequence[Any] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if float(self.initial_cash) <= 0:
            raise ValueError("initial_cash must be greater than 0")
        if not 0 <= float(self.commission_rate) < 1:
            raise ValueError("commission_rate must be between 0 and 1")
        if not 0 <= float(self.slippage_rate) < 1:
            raise ValueError("slippage_rate must be between 0 and 1")
        if str(self.execution_mode).strip().lower() not in {"next_open", "t_plus_one"}:
            raise ValueError("execution_mode must be next_open or t_plus_one")

        object.__setattr__(self, "initial_cash", float(self.initial_cash))
        object.__setattr__(self, "commission_rate", float(self.commission_rate))
        object.__setattr__(self, "slippage_rate", float(self.slippage_rate))
        object.__setattr__(self, "execution_mode", str(self.execution_mode).strip().lower())
        object.__setattr__(self, "buy_rules", tuple(self.buy_rules or ()))
        object.__setattr__(self, "sell_rules", tuple(self.sell_rules or ()))


@dataclass(frozen=True)
class Trade:
    """One executed trade."""

    trade_type: TradeType
    date: date
    price: float
    shares: int
    commission: float
    profit: float | None = None
    profit_rate: float | None = None


@dataclass(frozen=True)
class EquityPoint:
    """Daily equity snapshot after execution and market close."""

    date: date
    equity: float
    cash: float
    position_value: float
    drawdown: float


@dataclass(frozen=True)
class BacktestSummary:
    """Aggregated summary metrics for one backtest run."""

    total_return: float
    max_drawdown: float
    win_rate: float | None
    trade_count: int
    avg_holding_days: float | None


@dataclass(frozen=True)
class BacktestResult:
    """Result container for one backtest run."""

    trades: list[Trade]
    equity_points: list[EquityPoint]
    summary: BacktestSummary


class StrategyBacktestEngine:
    """Pure T+1 daily-bar backtest engine."""

    _REQUIRED_COLUMNS = ("date", "open", "close")
    _LOT_SIZE = 100

    def run(self, df: pd.DataFrame, config: BacktestConfig) -> BacktestResult:
        """Run a long-only single-position backtest over a daily OHLC frame."""

        prepared_df = self._prepare_frame(df)
        enriched_df = calc_indicators(prepared_df, self._normalize_indicator_config(config.indicators))
        buy_signals = evaluate_rules(enriched_df, list(config.buy_rules))
        sell_signals = evaluate_rules(enriched_df, list(config.sell_rules))

        trades: list[Trade] = []
        equity_points: list[EquityPoint] = []
        holding_days: list[int] = []

        cash = config.initial_cash
        position_shares = 0
        peak_equity = config.initial_cash
        pending_order: PendingOrder | None = None

        entry_price: float | None = None
        entry_date: date | None = None
        entry_commission = 0.0
        entry_index: int | None = None

        row_count = len(enriched_df.index)

        for idx, row in enriched_df.iterrows():
            current_date = self._coerce_date(row["date"])
            open_price = self._coerce_price(row["open"], column_name="open", current_date=current_date)
            close_price = self._coerce_price(row["close"], column_name="close", current_date=current_date)

            if pending_order == "buy":
                if position_shares == 0:
                    executed_price = open_price * (1 + config.slippage_rate)
                    shares, cash = self._execute_buy(price=executed_price, cash=cash, config=config)
                    if shares > 0:
                        entry_commission = self._calculate_commission(
                            price=executed_price,
                            shares=shares,
                            commission_rate=config.commission_rate,
                        )
                        position_shares = shares
                        entry_price = executed_price
                        entry_date = current_date
                        entry_index = idx
                        trades.append(
                            Trade(
                                trade_type="buy",
                                date=current_date,
                                price=executed_price,
                                shares=shares,
                                commission=entry_commission,
                            )
                        )
                pending_order = None
            elif pending_order == "sell":
                if position_shares > 0 and entry_price is not None and entry_date is not None and entry_index is not None:
                    executed_price = open_price * (1 - config.slippage_rate)
                    exit_commission = self._calculate_commission(
                        price=executed_price,
                        shares=position_shares,
                        commission_rate=config.commission_rate,
                    )
                    proceeds = self._execute_sell(price=executed_price, shares=position_shares, config=config)
                    cash += proceeds

                    cost_basis = entry_price * position_shares + entry_commission
                    profit = proceeds - cost_basis
                    profit_rate = None if cost_basis == 0 else profit / cost_basis
                    holding_days.append(idx - entry_index)

                    trades.append(
                        Trade(
                            trade_type="sell",
                            date=current_date,
                            price=executed_price,
                            shares=position_shares,
                            commission=exit_commission,
                            profit=profit,
                            profit_rate=profit_rate,
                        )
                    )

                    position_shares = 0
                    entry_price = None
                    entry_date = None
                    entry_commission = 0.0
                    entry_index = None
                pending_order = None

            if idx < row_count - 1:
                if position_shares == 0:
                    if bool(buy_signals.iloc[idx]):
                        pending_order = "buy"
                elif bool(sell_signals.iloc[idx]):
                    pending_order = "sell"

            equity_point, peak_equity = self._track_equity(
                current_date=current_date,
                cash=cash,
                position_shares=position_shares,
                close_price=close_price,
                peak_equity=peak_equity,
            )
            equity_points.append(equity_point)

        summary = self._calculate_summary(
            initial_cash=config.initial_cash,
            trades=trades,
            equity_points=equity_points,
            holding_days=holding_days,
        )
        return BacktestResult(trades=trades, equity_points=equity_points, summary=summary)

    def _execute_buy(self, price: float, cash: float, config: BacktestConfig) -> tuple[int, float]:
        """Calculate filled shares and remaining cash for one buy order."""

        if price <= 0:
            raise ValueError("Buy price must be greater than 0")
        if cash < 0:
            raise ValueError("cash must not be negative")

        available_cash = cash * (1 - config.commission_rate)
        raw_lots = math.floor(available_cash / price / self._LOT_SIZE)
        shares = raw_lots * self._LOT_SIZE
        if shares <= 0:
            return 0, cash

        commission = self._calculate_commission(
            price=price,
            shares=shares,
            commission_rate=config.commission_rate,
        )
        remaining_cash = cash - price * shares - commission
        if remaining_cash < 0 and math.isclose(remaining_cash, 0.0, abs_tol=1e-9):
            remaining_cash = 0.0
        return shares, remaining_cash

    def _execute_sell(self, price: float, shares: int, config: BacktestConfig) -> float:
        """Calculate net cash received from one sell order."""

        if price <= 0:
            raise ValueError("Sell price must be greater than 0")
        if shares <= 0:
            raise ValueError("shares must be greater than 0")

        commission = self._calculate_commission(
            price=price,
            shares=shares,
            commission_rate=config.commission_rate,
        )
        return price * shares - commission

    def _track_equity(
        self,
        *,
        current_date: date,
        cash: float,
        position_shares: int,
        close_price: float,
        peak_equity: float,
    ) -> tuple[EquityPoint, float]:
        """Create one daily equity point and update the running peak."""

        position_value = position_shares * close_price
        equity = cash + position_value
        peak_equity = max(peak_equity, equity)
        drawdown = 0.0 if peak_equity == 0 else (peak_equity - equity) / peak_equity
        return (
            EquityPoint(
                date=current_date,
                equity=equity,
                cash=cash,
                position_value=position_value,
                drawdown=drawdown,
            ),
            peak_equity,
        )

    def _calculate_summary(
        self,
        *,
        initial_cash: float,
        trades: Sequence[Trade],
        equity_points: Sequence[EquityPoint],
        holding_days: Sequence[int],
    ) -> BacktestSummary:
        """Aggregate equity and trade data into summary statistics."""

        final_equity = equity_points[-1].equity if equity_points else initial_cash
        closed_trades = [trade for trade in trades if trade.trade_type == "sell"]
        winning_trades = [
            trade for trade in closed_trades if trade.profit is not None and trade.profit > 0
        ]

        win_rate = None if not closed_trades else len(winning_trades) / len(closed_trades)
        avg_holding_days = None if not holding_days else sum(holding_days) / len(holding_days)
        max_drawdown = max((point.drawdown for point in equity_points), default=0.0)

        return BacktestSummary(
            total_return=(final_equity - initial_cash) / initial_cash,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            trade_count=len(closed_trades),
            avg_holding_days=avg_holding_days,
        )

    @classmethod
    def _prepare_frame(cls, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            raise ValueError("Backtest DataFrame must not be empty")

        cls._require_columns(df, cls._REQUIRED_COLUMNS)

        prepared = df.copy(deep=True)
        try:
            prepared["date"] = pd.to_datetime(prepared["date"]).dt.date
        except (TypeError, ValueError) as exc:
            raise ValueError("date column must be parseable as dates") from exc

        prepared = prepared.sort_values("date").reset_index(drop=True)
        return prepared

    @staticmethod
    def _normalize_indicator_config(indicators: Mapping[str, Any] | Any | None) -> dict[str, Any] | None:
        if indicators is None:
            return None
        if isinstance(indicators, Mapping):
            raw_config = dict(indicators)
        elif hasattr(indicators, "model_dump"):
            raw_config = indicators.model_dump(exclude_none=True)
        else:
            raise ValueError("indicators must be a mapping or a model with model_dump()")
        return {key: value for key, value in raw_config.items() if value is not None}

    @staticmethod
    def _require_columns(df: pd.DataFrame, columns: Sequence[str]) -> None:
        missing = [column for column in columns if column not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

    @staticmethod
    def _coerce_date(value: Any) -> date:
        if isinstance(value, date):
            return value
        try:
            return pd.Timestamp(value).date()
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid date value: {value!r}") from exc

    @staticmethod
    def _coerce_price(value: Any, *, column_name: str, current_date: date) -> float:
        try:
            normalized = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{column_name} must be numeric on {current_date.isoformat()}") from exc

        if math.isnan(normalized) or math.isinf(normalized) or normalized <= 0:
            raise ValueError(f"{column_name} must be greater than 0 on {current_date.isoformat()}")
        return normalized

    @staticmethod
    def _calculate_commission(*, price: float, shares: int, commission_rate: float) -> float:
        return price * shares * commission_rate


__all__ = [
    "BacktestConfig",
    "BacktestResult",
    "BacktestSummary",
    "EquityPoint",
    "StrategyBacktestEngine",
    "Trade",
]
