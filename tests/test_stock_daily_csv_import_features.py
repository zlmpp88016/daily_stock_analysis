from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from scripts.import_stock_daily_csv import (
    CanonicalRow,
    PreInsertHookContext,
    apply_pre_insert_hook,
    connect_import_db,
    load_pre_insert_hook,
    resolve_import_files,
)


def _make_row() -> CanonicalRow:
    return CanonicalRow(
        file_path=str(Path(r"E:\learning\stock\stock\input\2026-03-19.csv")),
        row_num=2,
        code="600000",
        name="PF Bank",
        trade_date=date(2026, 3, 19),
        open_price=10.1,
        high_price=10.5,
        low_price=10.0,
        close_price=10.3,
        volume=1000.0,
        amount=10300.0,
        pct_chg=1.2,
        data_source="csv_stock_daily_import",
    )


def _make_context() -> PreInsertHookContext:
    return PreInsertHookContext(
        file_path=Path(r"E:\learning\stock\stock\input\2026-03-19.csv"),
        file_date=date(2026, 3, 19),
        header_version="v2",
        data_source="csv_stock_daily_import",
    )


def test_resolve_import_files_supports_single_file_outside_year_tree(tmp_path: Path) -> None:
    single_file = tmp_path / "manual-import" / "2026-03-19.csv"
    single_file.parent.mkdir(parents=True, exist_ok=True)
    single_file.write_text("header\n", encoding="utf-8")

    files = resolve_import_files(
        source_root=tmp_path / "missing-root",
        start_year=2000,
        end_year=2026,
        single_file=single_file,
    )

    assert files == [single_file.resolve()]


def test_apply_pre_insert_hook_can_transform_rows() -> None:
    row = _make_row()
    context = _make_context()

    transformed = apply_pre_insert_hook(
        row,
        hook=lambda current, ctx: replace(current, data_source=f"{ctx.data_source}_hooked", name="PF Bank Hooked"),
        context=context,
    )

    assert transformed is not None
    assert transformed.data_source == "csv_stock_daily_import_hooked"
    assert transformed.name == "PF Bank Hooked"


def test_apply_pre_insert_hook_can_skip_rows() -> None:
    result = apply_pre_insert_hook(
        _make_row(),
        hook=lambda current, ctx: None,
        context=_make_context(),
    )

    assert result is None


def test_load_pre_insert_hook_imports_callable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module_path = tmp_path / "sample_import_hook.py"
    module_path.write_text(
        "from dataclasses import replace\n"
        "\n"
        "def transform_row(row, context):\n"
        "    return replace(row, data_source=context.data_source + '_plugin')\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    hook = load_pre_insert_hook("sample_import_hook:transform_row")

    transformed = apply_pre_insert_hook(_make_row(), hook=hook, context=_make_context())

    assert transformed is not None
    assert transformed.data_source.endswith("_plugin")


def test_load_pre_insert_hook_rejects_invalid_format() -> None:
    with pytest.raises(ValueError):
        load_pre_insert_hook("sample_import_hook")


def test_connect_import_db_enables_autocommit(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakePsycopg:
        def connect(self, dsn: str, *, autocommit: bool):
            captured["dsn"] = dsn
            captured["autocommit"] = autocommit
            return "fake-connection"

    import scripts.import_stock_daily_csv as import_script

    monkeypatch.setattr(import_script, "psycopg", FakePsycopg())

    connection = connect_import_db("postgresql://example")

    assert connection == "fake-connection"
    assert captured == {"dsn": "postgresql://example", "autocommit": True}
