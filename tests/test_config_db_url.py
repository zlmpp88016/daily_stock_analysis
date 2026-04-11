# -*- coding: utf-8 -*-
"""Tests for Config.get_db_url selection logic."""
from pathlib import Path

from src.config import Config


def _make_config(**overrides) -> Config:
    cfg = Config()
    for key, value in overrides.items():
        setattr(cfg, key, value)
    return cfg


def test_db_url_uses_database_url_override():
    cfg = _make_config(
        database_url="postgresql+psycopg://override",
        postgres_host="pg.local",
        postgres_db="stock",
        postgres_user="user",
        postgres_password="pass",
    )
    assert cfg.get_db_url() == "postgresql+psycopg://override"


def test_db_url_rewrites_plain_postgres_scheme():
    cfg = _make_config(database_url="postgresql://user:pass@host:5432/db")
    assert cfg.get_db_url().startswith("postgresql+psycopg://")


def test_db_url_uses_postgres_fields_when_complete():
    cfg = _make_config(
        postgres_host="pg.local",
        postgres_port=5433,
        postgres_db="stock",
        postgres_user="user",
        postgres_password="pass",
        postgres_sslmode="require",
    )
    assert cfg.get_db_url() == "postgresql+psycopg://user:pass@pg.local:5433/stock?sslmode=require"


def test_db_url_falls_back_to_sqlite_when_incomplete(tmp_path: Path):
    sqlite_path = tmp_path / "db.sqlite"
    cfg = _make_config(
        postgres_host="pg.local",
        postgres_db=None,
        postgres_user=None,
        database_path=str(sqlite_path),
    )
    expected = f"sqlite:///{sqlite_path.resolve()}"
    result = cfg.get_db_url()
    assert result == expected
    assert sqlite_path.parent.exists()


def test_db_url_uses_sqlite_by_default(tmp_path: Path):
    sqlite_path = tmp_path / "stock_analysis.db"
    cfg = _make_config(database_path=str(sqlite_path))
    expected = f"sqlite:///{sqlite_path.resolve()}"
    assert cfg.get_db_url() == expected
    assert sqlite_path.parent.exists()
