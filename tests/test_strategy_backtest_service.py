# -*- coding: utf-8 -*-
"""Integration tests for strategy backtest service and repository."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import MagicMock

from src.config import Config
from src.repositories.strategy_backtest_repo import StrategyBacktestRepository
from src.services.strategy_backtest_service import StrategyBacktestService
from src.storage import DatabaseManager, StockDaily


class StrategyBacktestServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self._db_path = os.path.join(self._temp_dir.name, "strategy_backtest_service.db")
        self._original_env = {
            key: os.environ.get(key)
            for key in (
                "DATABASE_URL",
                "DATABASE_PATH",
                "POSTGRES_HOST",
                "POSTGRES_PORT",
                "POSTGRES_DB",
                "POSTGRES_USER",
                "POSTGRES_PASSWORD",
                "POSTGRES_SSLMODE",
            )
        }
        os.environ["DATABASE_URL"] = f"sqlite:///{self._db_path}"
        os.environ["DATABASE_PATH"] = self._db_path
        for key in ("POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_SSLMODE"):
            os.environ.pop(key, None)

        Config.reset_instance()
        DatabaseManager.reset_instance()
        self.db = DatabaseManager.get_instance()
        self._seed_daily_rows()

    def tearDown(self) -> None:
        DatabaseManager.reset_instance()
        Config.reset_instance()
        for key, value in self._original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._temp_dir.cleanup()

    def _seed_daily_rows(self) -> None:
        rows = [
            StockDaily(
                code="600519",
                name="Test Stock",
                date=datetime(2024, 1, 1).date(),
                open=9.0,
                high=9.5,
                low=8.8,
                close=9.0,
                volume=1000.0,
                amount=9000.0,
                pct_chg=0.0,
                data_source="UnitTestSeed",
            ),
            StockDaily(
                code="600519",
                name="Test Stock",
                date=datetime(2024, 1, 2).date(),
                open=10.0,
                high=11.2,
                low=9.8,
                close=11.0,
                volume=1200.0,
                amount=13200.0,
                pct_chg=22.22,
                data_source="UnitTestSeed",
            ),
            StockDaily(
                code="600519",
                name="Test Stock",
                date=datetime(2024, 1, 3).date(),
                open=11.0,
                high=12.2,
                low=10.8,
                close=12.0,
                volume=1300.0,
                amount=15600.0,
                pct_chg=9.09,
                data_source="UnitTestSeed",
            ),
            StockDaily(
                code="600519",
                name="Test Stock",
                date=datetime(2024, 1, 4).date(),
                open=11.0,
                high=11.2,
                low=8.9,
                close=9.0,
                volume=1400.0,
                amount=12600.0,
                pct_chg=-25.0,
                data_source="UnitTestSeed",
            ),
            StockDaily(
                code="600519",
                name="Test Stock",
                date=datetime(2024, 1, 5).date(),
                open=9.0,
                high=9.5,
                low=8.5,
                close=9.0,
                volume=1100.0,
                amount=9900.0,
                pct_chg=0.0,
                data_source="UnitTestSeed",
            ),
        ]

        with self.db.session_scope() as session:
            session.add_all(rows)

    def test_run_backtest_persists_run_trade_and_equity_from_database(self) -> None:
        fetcher_manager = MagicMock()
        service = StrategyBacktestService(
            self.db,
            fetcher_manager=fetcher_manager,
        )

        run = service.run_backtest(
            code="600519",
            start_date=datetime(2024, 1, 1).date(),
            end_date=datetime(2024, 1, 5).date(),
            initial_cash=2000.0,
            indicators={},
            buy_rules=["close > 10"],
            sell_rules=["close < 10"],
        )

        fetcher_manager.get_daily_data.assert_not_called()
        self.assertEqual(run["code"], "600519")
        self.assertEqual(run["status"], "completed")
        self.assertEqual(run["trade_count"], 1)
        self.assertAlmostEqual(run["total_return"], -0.1)
        self.assertEqual(run["buy_rules"], ["close > 10"])
        self.assertEqual(run["sell_rules"], ["close < 10"])
        self.assertEqual(run["indicators"], {})

        history = service.get_history(code="600519", limit=10)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["id"], run["id"])

        detail = service.get_run_detail(run["id"])
        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertEqual(detail["id"], run["id"])
        self.assertEqual(len(detail["trades"]), 2)
        self.assertEqual(len(detail["equity_curve"]), 5)
        self.assertEqual(detail["trades"][0]["trade_type"], "buy")
        self.assertEqual(detail["trades"][1]["trade_type"], "sell")

        repo = StrategyBacktestRepository(self.db)
        repo_history = repo.get_history(code="600519", limit=10)
        self.assertEqual(len(repo_history), 1)
        repo_run = repo.get_run(run["id"])
        self.assertIsNotNone(repo_run)
        assert repo_run is not None
        self.assertEqual(len(repo_run["trades"]), 2)
        self.assertEqual(len(repo_run["equity_curve"]), 5)

        with self.db.get_session() as session:
            cached_rows = session.query(StockDaily).filter(StockDaily.code == "600519").count()
        self.assertEqual(cached_rows, 5)

    def test_run_backtest_rejects_missing_database_range(self) -> None:
        fetcher_manager = MagicMock()
        service = StrategyBacktestService(
            self.db,
            fetcher_manager=fetcher_manager,
        )

        with self.assertRaises(ValueError) as context:
            service.run_backtest(
                code="600519",
                start_date=datetime(2025, 1, 1).date(),
                end_date=datetime(2025, 1, 5).date(),
                initial_cash=2000.0,
                indicators={},
                buy_rules=["close > 10"],
                sell_rules=["close < 10"],
            )

        fetcher_manager.get_daily_data.assert_not_called()
        self.assertIn("No historical data found in database", str(context.exception))


if __name__ == "__main__":
    unittest.main()
