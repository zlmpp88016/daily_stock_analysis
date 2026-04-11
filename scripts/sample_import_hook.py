from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scripts.import_stock_daily_csv import CanonicalRow, PreInsertHookContext


def transform_row(row: CanonicalRow, context: PreInsertHookContext) -> CanonicalRow | None:
    """Sample hook for `--pre-insert-hook`.

    Keep the row unchanged by default. Replace this logic with custom filtering or
    value normalization before rows enter the staging table.
    """
    return replace(row, data_source=f"{context.data_source}_hooked")
