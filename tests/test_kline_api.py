# -*- coding: utf-8 -*-
"""Integration tests for K-line API endpoints."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
from fastapi.testclient import TestClient

try:
    import litellm  # noqa: F401
except ModuleNotFoundError:
    sys.modules["litellm"] = MagicMock()

import src.auth as auth
from api.app import create_app
from data_provider.realtime_types import ChipDistribution
from src.config import Config
from src.storage import DatabaseManager, StockDaily


class _FakeFetcherManager:
    def get_chip_distribution(self, stock_code: str):
        if stock_code != "600519":
            return None
        return ChipDistribution(
            code=stock_code,
            profit_ratio=0.56,
            avg_cost=1880.5,
            cost_90_low=1801.0,
            cost_90_high=1936.0,
            concentration_90=0.12,
            cost_70_low=1835.0,
            cost_70_high=1910.0,
            concentration_70=0.08,
        )


class KlineApiTestCase(unittest.TestCase):
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
        os.environ["DATABASE_URL"] = f"sqlite:///{self.data_dir / 'kline_api.db'}"
        os.environ["DATABASE_PATH"] = str(self.data_dir / "kline_api.db")
        for key in ("POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_SSLMODE"):
            os.environ.pop(key, None)

        Config.reset_instance()
        DatabaseManager.reset_instance()
        auth._auth_enabled = None

        self.auth_patcher = patch.object(auth, "_is_auth_enabled_from_env", return_value=False)
        self.fetcher_patcher = patch("api.v1.endpoints.kline.DataFetcherManager", return_value=_FakeFetcherManager())
        self.auth_patcher.start()
        self.fetcher_patcher.start()

        self.db = DatabaseManager.get_instance()
        self._seed_daily_rows()

        app = create_app(static_dir=self.data_dir / "empty-static")
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.fetcher_patcher.stop()
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
        dates = pd.bdate_range("2024-01-02", periods=40)
        previous_close = None
        rows = []
        for index, current in enumerate(dates):
            close = 100.0 + index
            pct_chg = 0.0 if previous_close is None else ((close - previous_close) / previous_close) * 100
            volume = 1000.0 + index * 25
            rows.append(
                StockDaily(
                    code="600519",
                    name="Test Stock",
                    date=current.date(),
                    open=close - 1.0,
                    high=close + 2.0,
                    low=close - 2.5,
                    close=close,
                    volume=volume,
                    amount=close * volume,
                    pct_chg=pct_chg,
                    data_source="TestFixture",
                )
            )
            previous_close = close

        with self.db.session_scope() as session:
            session.add_all(rows)

    def test_get_kline_daily_returns_valid_json(self) -> None:
        response = self.client.get("/api/v1/kline/600519", params={"period": "daily", "limit": 5})
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["code"], "600519")
        self.assertEqual(payload["name"], "Test Stock")
        self.assertEqual(payload["period"], "daily")
        self.assertEqual(len(payload["bars"]), 5)
        self.assertEqual(len(payload["indicators"]), 5)
        self.assertIsInstance(payload["bars"][0]["date"], str)
        self.assertIsInstance(payload["bars"][0]["close"], float)
        self.assertIsNotNone(payload["indicators"][-1]["macd_dif"])
        self.assertIsNotNone(payload["indicators"][-1]["boll_middle"])

    def test_get_kline_weekly_and_chip_distribution(self) -> None:
        kline_response = self.client.get("/api/v1/kline/600519", params={"period": "weekly", "limit": 10})
        self.assertEqual(kline_response.status_code, 200)

        kline_payload = kline_response.json()
        self.assertEqual(kline_payload["period"], "weekly")
        self.assertGreater(len(kline_payload["bars"]), 0)
        self.assertEqual(len(kline_payload["bars"]), len(kline_payload["indicators"]))

        chip_response = self.client.get("/api/v1/kline/600519/chip-distribution")
        self.assertEqual(chip_response.status_code, 200)

        chip_payload = chip_response.json()
        self.assertEqual(chip_payload["code"], "600519")
        self.assertEqual(chip_payload["avg_cost"], 1880.5)
        self.assertEqual(chip_payload["concentration_90"], 0.12)

    def test_invalid_period_returns_400(self) -> None:
        response = self.client.get("/api/v1/kline/600519", params={"period": "hourly"})
        self.assertEqual(response.status_code, 400)

        payload = response.json()
        self.assertEqual(payload["error"], "invalid_request")
        self.assertIn("period must be one of", payload["message"])


if __name__ == "__main__":
    unittest.main()
