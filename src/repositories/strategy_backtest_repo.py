# -*- coding: utf-8 -*-
"""Repository helpers for strategy backtest persistence."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from src.storage import (
    DatabaseManager,
    StrategyBacktestEquity,
    StrategyBacktestRun,
    StrategyBacktestTrade,
)
from src.strategy_backtest.engine import EquityPoint, Trade

logger = logging.getLogger(__name__)


class StrategyBacktestRepository:
    """Database access layer for strategy backtest runs and child records."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager.get_instance()

    def save_run(
        self,
        run: StrategyBacktestRun,
        *,
        session: Optional[Session] = None,
    ) -> StrategyBacktestRun:
        """Persist one strategy backtest run."""
        if session is not None:
            session.add(run)
            session.flush()
            session.refresh(run)
            return run

        with self.db.get_session() as local_session:
            try:
                local_session.add(run)
                local_session.commit()
                local_session.refresh(run)
                return run
            except Exception as exc:
                local_session.rollback()
                logger.error("Failed to save strategy backtest run: %s", exc)
                raise

    def get_run(
        self,
        run_id: int,
        *,
        session: Optional[Session] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return one strategy backtest run with its trades and equity curve."""
        if session is not None:
            return self._get_run_with_children(session=session, run_id=run_id)

        with self.db.get_session() as local_session:
            return self._get_run_with_children(session=local_session, run_id=run_id)

    def get_history(self, *, code: Optional[str] = None, limit: int = 20) -> List[StrategyBacktestRun]:
        """Return recent strategy backtest runs."""
        with self.db.get_session() as session:
            query = select(StrategyBacktestRun)
            if code:
                query = query.where(StrategyBacktestRun.code == code)

            rows = (
                session.execute(
                    query.order_by(
                        desc(StrategyBacktestRun.created_at),
                        desc(StrategyBacktestRun.id),
                    ).limit(limit)
                )
                .scalars()
                .all()
            )
            return list(rows)

    def save_trades(
        self,
        run_id: int,
        trades: Sequence[Trade],
        *,
        session: Optional[Session] = None,
    ) -> List[StrategyBacktestTrade]:
        """Persist trade rows for one run."""
        rows = [
            StrategyBacktestTrade(
                run_id=run_id,
                trade_type=trade.trade_type,
                trade_date=trade.date,
                price=trade.price,
                shares=trade.shares,
                commission=trade.commission,
                profit=trade.profit,
                profit_rate=trade.profit_rate,
            )
            for trade in trades
        ]
        if not rows:
            return []

        if session is not None:
            session.add_all(rows)
            session.flush()
            return rows

        with self.db.get_session() as local_session:
            try:
                local_session.add_all(rows)
                local_session.commit()
                return rows
            except Exception as exc:
                local_session.rollback()
                logger.error("Failed to save strategy backtest trades: %s", exc)
                raise

    def save_equity(
        self,
        run_id: int,
        equity_points: Sequence[EquityPoint],
        *,
        session: Optional[Session] = None,
    ) -> List[StrategyBacktestEquity]:
        """Persist equity curve rows for one run."""
        rows = [
            StrategyBacktestEquity(
                run_id=run_id,
                date=point.date,
                equity=point.equity,
                cash=point.cash,
                position_value=point.position_value,
                drawdown=point.drawdown,
            )
            for point in equity_points
        ]
        if not rows:
            return []

        if session is not None:
            session.add_all(rows)
            session.flush()
            return rows

        with self.db.get_session() as local_session:
            try:
                local_session.add_all(rows)
                local_session.commit()
                return rows
            except Exception as exc:
                local_session.rollback()
                logger.error("Failed to save strategy backtest equity curve: %s", exc)
                raise

    @staticmethod
    def _get_run_with_children(session: Session, *, run_id: int) -> Optional[Dict[str, Any]]:
        run = session.execute(
            select(StrategyBacktestRun).where(StrategyBacktestRun.id == run_id).limit(1)
        ).scalar_one_or_none()
        if run is None:
            return None

        trades = (
            session.execute(
                select(StrategyBacktestTrade)
                .where(StrategyBacktestTrade.run_id == run_id)
                .order_by(StrategyBacktestTrade.trade_date, StrategyBacktestTrade.id)
            )
            .scalars()
            .all()
        )
        equity_curve = (
            session.execute(
                select(StrategyBacktestEquity)
                .where(StrategyBacktestEquity.run_id == run_id)
                .order_by(StrategyBacktestEquity.date, StrategyBacktestEquity.id)
            )
            .scalars()
            .all()
        )

        return {
            "run": run,
            "trades": list(trades),
            "equity_curve": list(equity_curve),
        }
