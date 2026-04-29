# -*- coding: utf-8 -*-
"""Integration tests for strategy backtest API endpoints."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

try:
    import litellm  # noqa: F401
except ModuleNotFoundError:
    sys.modules["litellm"] = MagicMock()

import src.auth as auth
from api.app import create_app
from src.config import Config
from src.storage import DatabaseManager, StockDaily


class StrategyBacktestApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.env_path = self.data_dir / ".env"
        self.env_path.write_text(
            "STOCK_LIST=600519\nGEMINI_API_KEY=test\nADMIN_AUTH_ENABLED=false\n",
            encoding="utf-8",
        )

        self._original_env = {
            key: os.environ.get(key)
            for key in (
                "ENV_FILE",
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
        os.environ["ENV_FILE"] = str(self.env_path)
        os.environ["DATABASE_URL"] = f"sqlite:///{self.data_dir / 'strategy_backtest_api.db'}"
        os.environ["DATABASE_PATH"] = str(self.data_dir / "strategy_backtest_api.db")
        for key in ("POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_SSLMODE"):
            os.environ.pop(key, None)

        Config.reset_instance()
        DatabaseManager.reset_instance()
        auth._auth_enabled = None

        self.auth_patcher = patch.object(auth, "_is_auth_enabled_from_env", return_value=False)
        self.auth_patcher.start()

        self.db = DatabaseManager.get_instance()
        self._seed_daily_rows()

        app = create_app(static_dir=self.data_dir / "empty-static")
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.auth_patcher.stop()
        DatabaseManager.reset_instance()
        Config.reset_instance()
        for key, value in self._original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.temp_dir.cleanup()

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
                data_source="ApiSeed",
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
                data_source="ApiSeed",
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
                data_source="ApiSeed",
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
                data_source="ApiSeed",
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
                data_source="ApiSeed",
            ),
        ]

        with self.db.session_scope() as session:
            session.add_all(rows)

    @staticmethod
    def _payload() -> dict:
        return {
            "code": "600519",
            "start_date": "2024-01-01",
            "end_date": "2024-01-05",
            "initial_cash": 2000.0,
            "indicators": {},
            "buy_rules": ["close > 10"],
            "sell_rules": ["close < 10"],
        }

    def test_strategy_backtest_endpoints_cover_run_history_and_detail(self) -> None:
        run_response = self.client.post("/api/v1/strategy-backtest/run", json=self._payload())
        self.assertEqual(run_response.status_code, 200)
        run_data = run_response.json()
        self.assertEqual(run_data["code"], "600519")
        self.assertEqual(run_data["status"], "completed")
        self.assertEqual(run_data["trade_count"], 1)

        history_response = self.client.get("/api/v1/strategy-backtest/history", params={"code": "600519", "limit": 10})
        self.assertEqual(history_response.status_code, 200)
        history_data = history_response.json()
        self.assertEqual(len(history_data), 1)
        self.assertEqual(history_data[0]["id"], run_data["id"])

        detail_response = self.client.get(f"/api/v1/strategy-backtest/{run_data['id']}")
        self.assertEqual(detail_response.status_code, 200)
        detail_data = detail_response.json()
        self.assertEqual(detail_data["id"], run_data["id"])
        self.assertEqual(len(detail_data["trades"]), 2)
        self.assertEqual(len(detail_data["equity_curve"]), 5)

    def test_strategy_backtest_run_returns_400_when_database_data_missing(self) -> None:
        response = self.client.post(
            "/api/v1/strategy-backtest/run",
            json={
                **self._payload(),
                "start_date": "2025-01-01",
                "end_date": "2025-01-05",
            },
        )
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertIn("No historical data found in database", payload["message"])

    def test_strategy_backtest_detail_returns_404_for_missing_run(self) -> None:
        response = self.client.get("/api/v1/strategy-backtest/9999")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
