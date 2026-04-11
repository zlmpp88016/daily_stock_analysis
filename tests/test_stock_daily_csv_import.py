from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scripts.import_stock_daily_csv import (
    build_psycopg_dsn,
    collect_source_files,
    detect_header_version,
    normalize_csv_row,
)


def test_build_psycopg_dsn_rewrites_sqlalchemy_url() -> None:
    assert (
        build_psycopg_dsn("postgresql+psycopg://user:pass@pg.local:5432/stock?sslmode=require")
        == "postgresql://user:pass@pg.local:5432/stock?sslmode=require"
    )


def test_build_psycopg_dsn_rejects_non_postgres_url() -> None:
    with pytest.raises(ValueError):
        build_psycopg_dsn("sqlite:///tmp/demo.db")


def test_collect_source_files_filters_years_and_limit(tmp_path: Path) -> None:
    root = tmp_path / "daily"
    for year in ("1999", "2000", "2001", "2002"):
        year_dir = root / year
        year_dir.mkdir(parents=True, exist_ok=True)
        (year_dir / f"{year}-01-03.csv").write_text("header\n", encoding="utf-8")

    files = collect_source_files(root, start_year=2000, end_year=2001, limit=1)

    assert len(files) == 1
    assert files[0].name == "2000-01-03.csv"


def test_detect_header_version_supports_v1() -> None:
    header = ["序号", "代码", "名称", "日期", "昨收", "开盘", "收盘", "最高", "最低", "成交量", "成交额", "振幅", "涨跌幅"]
    assert detect_header_version(header) == "v1"


def test_detect_header_version_supports_v2() -> None:
    header = [
        "日期",
        "代码",
        "名称",
        "昨收",
        "开盘",
        "最高",
        "最低",
        "收盘",
        "成交量(股)",
        "成交额(元)",
        "涨跌(元)",
        "涨跌幅(%)",
        "换手率(%)",
        "流通股本(股)",
        "总股本(股)",
    ]
    assert detect_header_version(header) == "v2"


def test_normalize_csv_row_supports_v1() -> None:
    row = {
        "序号": "1",
        "代码": "sh600000",
        "名称": "浦发银行",
        "日期": "2000-01-04",
        "昨收": "24.75",
        "开盘": "24.98",
        "收盘": "25.57",
        "最高": "25.78",
        "最低": "24.75",
        "成交量": "44960",
        "成交额": "113946784",
        "振幅": "0.82",
        "涨跌幅": "3.313131313131313",
    }

    normalized = normalize_csv_row(
        row=row,
        header_version="v1",
        row_num=2,
        file_path=Path(r"E:\learning\stock\stock\增量\日线\2000\2000-01-04.csv"),
        file_date=date(2000, 1, 4),
        data_source="csv_stock_daily_import",
    )

    assert normalized.code == "600000"
    assert normalized.name == "浦发银行"
    assert normalized.trade_date == date(2000, 1, 4)
    assert normalized.open_price == 24.98
    assert normalized.close_price == 25.57
    assert normalized.volume == 44960.0


def test_normalize_csv_row_supports_v2() -> None:
    row = {
        "日期": "2026/1/12",
        "代码": "sz000001",
        "名称": "平安银行",
        "昨收": "12.10",
        "开盘": "12.11",
        "最高": "12.30",
        "最低": "12.02",
        "收盘": "12.25",
        "成交量(股)": "1000000",
        "成交额(元)": "12000000",
        "涨跌(元)": "0.15",
        "涨跌幅(%)": "1.239669421",
        "换手率(%)": "0.8",
        "流通股本(股)": "100000000",
        "总股本(股)": "100000000",
    }

    normalized = normalize_csv_row(
        row=row,
        header_version="v2",
        row_num=2,
        file_path=Path(r"E:\learning\stock\stock\增量\日线\2026\2026-01-12.csv"),
        file_date=date(2026, 1, 12),
        data_source="csv_stock_daily_import",
    )

    assert normalized.code == "000001"
    assert normalized.name == "平安银行"
    assert normalized.trade_date == date(2026, 1, 12)
    assert normalized.high_price == 12.30
    assert normalized.low_price == 12.02
    assert normalized.pct_chg == pytest.approx(1.239669421)


def test_normalize_csv_row_supports_bj_codes_in_v2() -> None:
    row = {
        "日期": "2026/1/12",
        "代码": "bj920809",
        "名称": "某北交所股票",
        "昨收": "10.00",
        "开盘": "10.10",
        "最高": "10.20",
        "最低": "9.98",
        "收盘": "10.05",
        "成交量(股)": "123456",
        "成交额(元)": "1234500",
        "涨跌(元)": "0.05",
        "涨跌幅(%)": "0.5",
        "换手率(%)": "1.2",
        "流通股本(股)": "10000000",
        "总股本(股)": "12000000",
    }

    normalized = normalize_csv_row(
        row=row,
        header_version="v2",
        row_num=2,
        file_path=Path(r"E:\learning\stock\stock\增量\日线\2026\2026-01-12.csv"),
        file_date=date(2026, 1, 12),
        data_source="csv_stock_daily_import",
    )

    assert normalized.code == "920809"
    assert normalized.name == "某北交所股票"


def test_normalize_csv_row_rejects_mismatched_trade_date() -> None:
    row = {
        "日期": "2026/1/13",
        "代码": "sh600000",
        "名称": "浦发银行",
        "开盘": "11.55",
        "最高": "11.68",
        "最低": "11.51",
        "收盘": "11.66",
        "成交量(股)": "60110100",
        "成交额(元)": "697500160",
        "涨跌幅(%)": "1.03",
    }

    with pytest.raises(ValueError):
        normalize_csv_row(
            row=row,
            header_version="v2",
            row_num=2,
            file_path=Path(r"E:\learning\stock\stock\增量\日线\2026\2026-01-12.csv"),
            file_date=date(2026, 1, 12),
            data_source="csv_stock_daily_import",
        )
