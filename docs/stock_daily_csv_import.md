# Stock Daily CSV Import

## Purpose

`scripts/import_stock_daily_csv.py` imports historical daily-bar CSV files into PostgreSQL with:

- year-range scanning (`2000+` by default)
- optional single-file import via `--file`
- header-name detection for both legacy and 2026 header variants
- stock code normalization via `src.services.stock_code_utils.normalize_code()`
- optional pre-insert hook via `--pre-insert-hook module:function`
- staging + manifest tables for resumable runs
- `ON CONFLICT (code, date)` merge into `public.stock_daily`
- SQL window-function backfill for `ma5`, `ma10`, and `ma20`

`volume_ratio` is intentionally left as `NULL` because the source files do not provide a confirmed historical formula.

## Important Notes

- The current source tree under `E:\learning\stock\stock\增量\日线` ends at `2026-03-19.csv`.
- The live PostgreSQL table `public.stock_daily` includes a required `name` column, so the importer writes `name` from CSV even though the local ORM model does not currently expose that field.
- Unknown headers fail fast and are recorded in `public.stock_daily_import_manifest`.

## Usage

```bash
python scripts/import_stock_daily_csv.py
python scripts/import_stock_daily_csv.py --start-year 2026 --end-year 2026 --limit-files 5
python scripts/import_stock_daily_csv.py --file E:\learning\stock\stock\增量\日线\2026\2026-03-19.csv
python scripts/import_stock_daily_csv.py --dry-run --start-year 2000 --end-year 2000 --limit-files 2
python scripts/import_stock_daily_csv.py --reprocess --start-year 2024 --end-year 2026
python scripts/import_stock_daily_csv.py --file E:\learning\stock\stock\增量\日线\2026\2026-03-19.csv --pre-insert-hook scripts.sample_import_hook:transform_row
```

## Pre-Insert Hook

Use `--pre-insert-hook module:function` to transform or skip normalized rows before they are copied into `public.stock_daily_stage`.

```python
from dataclasses import replace

def transform_row(row, context):
    if row.code.startswith("688"):
        return None
    return replace(row, data_source=f"{context.data_source}_filtered")
```

Hook contract:

- input: `CanonicalRow`, `PreInsertHookContext`
- return `CanonicalRow` to keep the row
- return `None` to skip the row before staging/import
- hook exceptions fail the current file and are recorded in `public.stock_daily_import_manifest`

## Tables Created By The Script

- `public.stock_daily_stage`
- `public.stock_daily_import_manifest`

## Validation Performed

After import, the script validates:

- duplicate `(code, date)` pairs in `public.stock_daily`
- total target row count against manifest `staged_row_count` when the target table started empty
- min/max `date` in `public.stock_daily`

## Environment

The script reuses repo database configuration:

- `DATABASE_URL`
- or `POSTGRES_HOST` / `POSTGRES_PORT` / `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_SSLMODE`
