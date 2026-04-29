# -*- coding: utf-8 -*-
"""Tests for stock list loading without implicit fallback codes."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from src.config import Config


class ConfigStockListTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env_path = Path(self.temp_dir.name) / ".env"
        self._original_env = {
            key: os.environ.get(key)
            for key in ("ENV_FILE", "STOCK_LIST")
        }

    def tearDown(self) -> None:
        Config.reset_instance()
        for key, value in self._original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.temp_dir.cleanup()

    def test_load_from_env_keeps_stock_list_empty_when_not_configured(self) -> None:
        self.env_path.write_text("GEMINI_API_KEY=test\n", encoding="utf-8")
        os.environ["ENV_FILE"] = str(self.env_path)
        os.environ.pop("STOCK_LIST", None)

        Config.reset_instance()
        config = Config.get_instance()

        self.assertEqual(config.stock_list, [])

    def test_refresh_stock_list_keeps_empty_when_env_and_file_missing(self) -> None:
        self.env_path.write_text("GEMINI_API_KEY=test\n", encoding="utf-8")
        os.environ["ENV_FILE"] = str(self.env_path)
        os.environ.pop("STOCK_LIST", None)

        Config.reset_instance()
        config = Config.get_instance()
        config.stock_list = ["600519"]

        config.refresh_stock_list()

        self.assertEqual(config.stock_list, [])

    def test_refresh_stock_list_uses_explicit_configuration(self) -> None:
        self.env_path.write_text("STOCK_LIST=600519,000001\nGEMINI_API_KEY=test\n", encoding="utf-8")
        os.environ["ENV_FILE"] = str(self.env_path)
        os.environ.pop("STOCK_LIST", None)

        Config.reset_instance()
        config = Config.get_instance()

        self.assertEqual(config.stock_list, ["600519", "000001"])


if __name__ == "__main__":
    unittest.main()
