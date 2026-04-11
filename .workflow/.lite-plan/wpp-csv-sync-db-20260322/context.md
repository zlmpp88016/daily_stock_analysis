# Lite Planex Planning Report

**Session**: `wpp-csv-sync-db-20260322`  
**Requirement Source**: `E:\work\python_ws\daily_stock_analysis\vibecoding\2026.3.22\stock_his_data\csv_sync_db.md`  
**Status**: Planning only. Exploration completed; execution tasks intentionally left pending because the request asks for a migration plan, not an implementation run.

## Summary

- Source CSV root: `E:\learning\stock\stock\增量\日线`
- Year partitions on disk: `1990` through `2026`
- Requirement scope should filter to `2000+`
- CSV files observed: `8614`
- Actual latest file on disk: `2026-03-19.csv`
- Header variants observed: `2`
- Existing PostgreSQL support in repo: `yes`
- Existing `stock_daily` ORM model in repo: `yes`

## Exploration Results

### E1: Source data profile

- The dataset is partitioned by year, with one CSV per trade date.
- Older files use header V1:

```text
序号,代码,名称,日期,昨收,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅
```

- Newer files beginning on `2026-01-12` use header V2:

```text
日期,代码,名称,昨收,开盘,最高,最低,收盘,成交量(股),成交额(元),涨跌(元),涨跌幅(%),换手率(%),流通股本(股),总股本(股)
```

- This means the importer must use header-name aliases, not positional indexing.

### E2: Repo and database integration

- `E:\work\python_ws\daily_stock_analysis\src\storage.py` already defines `stock_daily`.
- `E:\work\python_ws\daily_stock_analysis\src\config.py` already builds PostgreSQL URLs using `psycopg`.
- `E:\work\python_ws\daily_stock_analysis\requirements.txt` already includes `psycopg[binary]`.
- The current `save_daily_data()` path is ORM row-by-row upsert and is not the recommended backfill strategy for this corpus.

### E3: Mapping and risk

- The source CSV can fill:
  `code`, `date`, `open`, `high`, `low`, `close`, `volume`, `amount`, `pct_chg`
- The source CSV does not fill directly:
  `ma5`, `ma10`, `ma20`, `volume_ratio`
- Existing repo conventions normalize `sh600000` / `sz000001` to bare digits. The migration should preserve this convention unless the application is refactored everywhere else.

## Recommended Migration Approach

1. Add a dedicated importer instead of reusing ORM row-by-row writes.
2. Filter source files to year directories `2000` through `2026`.
3. Detect CSV header version from the first line and map fields by header aliases.
4. Normalize codes with existing repo logic so persisted `code` values match current query behavior.
5. Load normalized rows into a staging table using `psycopg` `COPY`.
6. Merge from staging into `stock_daily` with `ON CONFLICT (code, date) DO UPDATE`.
7. Backfill `ma5`, `ma10`, and `ma20` after raw bars are loaded.
8. Leave `volume_ratio` as `NULL` unless a confirmed formula is provided.
9. Record file-level progress in an import manifest so the run can resume safely.
10. Validate row counts, min/max dates, duplicate constraints, and sample rows after each year or batch.

## Planned Execution Tasks

| Task | Wave | Goal |
|------|------|------|
| T1 | 1 | Freeze source-to-target mapping and normalization rules |
| T2 | 2 | Build resumable bulk importer with header detection |
| T3 | 2 | Create stage/manifest tables and merge SQL |
| T4 | 3 | Backfill moving averages and define `volume_ratio` handling |
| T5 | 4 | Produce validation checklist and operator runbook |

## Key Decisions

- Store normalized bare-digit stock codes to match current repo behavior.
- Use `COPY` + staging + `ON CONFLICT` for scale and idempotency.
- Treat `volume_ratio` as a follow-up decision, not a guessed value.
- Document the note/data mismatch explicitly: the note says `2026-03-20`, but the current filesystem ends at `2026-03-19`.

## Notable Risks

- CSV schema drift already exists and may expand again after `2026-03-19`.
- `volume_ratio` semantics are ambiguous for historical daily bars.
- The DDL comment examples and the repo’s current code-format convention are inconsistent; loading prefixed codes into `stock_daily` would likely break existing queries.
