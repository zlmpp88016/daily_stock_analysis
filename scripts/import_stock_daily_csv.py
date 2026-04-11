from __future__ import annotations

import argparse
import csv
import importlib
import logging
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    # Allow `python scripts/import_stock_daily_csv.py` from the repo root.
    sys.path.insert(0, str(PROJECT_ROOT))


from src.config import get_config
from src.services.stock_code_utils import normalize_code
from data_provider.base import normalize_stock_code

try:
    import psycopg
except ImportError:  # pragma: no cover - exercised only when dependency is missing.
    psycopg = None


LOGGER = logging.getLogger("stock_daily_csv_import")

DEFAULT_SOURCE_ROOT = Path(r"E:\learning\stock\stock\增量\日线")
DEFAULT_DATA_SOURCE = "csv_stock_daily_import"
SUPPORTED_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "gbk")

HEADER_MAPPINGS: dict[str, dict[str, tuple[str, ...]]] = {
    "v1": {
        "code": ("代码",),
        "name": ("名称",),
        "date": ("日期",),
        "open": ("开盘",),
        "high": ("最高",),
        "low": ("最低",),
        "close": ("收盘",),
        "volume": ("成交量",),
        "amount": ("成交额",),
        "pct_chg": ("涨跌幅",),
    },
    "v2": {
        "code": ("代码",),
        "name": ("名称",),
        "date": ("日期",),
        "open": ("开盘",),
        "high": ("最高",),
        "low": ("最低",),
        "close": ("收盘",),
        "volume": ("成交量(股)",),
        "amount": ("成交额(元)",),
        "pct_chg": ("涨跌幅(%)",),
    },
}


@dataclass(frozen=True)
class CanonicalRow:
    file_path: str
    row_num: int
    code: str
    name: str
    trade_date: date
    open_price: float | None
    high_price: float | None
    low_price: float | None
    close_price: float | None
    volume: float | None
    amount: float | None
    pct_chg: float | None
    data_source: str

    def to_stage_tuple(self) -> tuple[object, ...]:
        return (
            self.file_path,
            self.row_num,
            self.code,
            self.name,
            self.trade_date,
            self.open_price,
            self.high_price,
            self.low_price,
            self.close_price,
            self.volume,
            self.amount,
            self.pct_chg,
            self.data_source,
        )


@dataclass(frozen=True)
class CanonicalBatch:
    rows: list[CanonicalRow]
    source_row_count: int

    @property
    def staged_row_count(self) -> int:
        return len(self.rows)


@dataclass(frozen=True)
class PreInsertHookContext:
    file_path: Path
    file_date: date
    header_version: str
    data_source: str


PreInsertHook = Callable[[CanonicalRow, PreInsertHookContext], CanonicalRow | None]


@dataclass(frozen=True)
class FileProcessResult:
    file_path: Path
    header_version: str
    source_row_count: int
    staged_row_count: int
    skipped: bool = False

    @property
    def row_count(self) -> int:
        return self.staged_row_count


def build_psycopg_dsn(database_url: str) -> str:
    value = (database_url or "").strip()
    if not value:
        raise ValueError("Database URL is empty.")
    if value.startswith("postgresql+psycopg://"):
        return value.replace("postgresql+psycopg://", "postgresql://", 1)
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql://", 1)
    if value.startswith("postgresql://"):
        return value
    raise ValueError(f"Database URL must point to PostgreSQL, got: {value}")


def collect_source_files(
    source_root: Path,
    start_year: int,
    end_year: int,
    limit: int | None = None,
) -> list[Path]:
    if start_year > end_year:
        raise ValueError("start_year must be less than or equal to end_year.")
    if not source_root.exists():
        raise FileNotFoundError(f"Source root does not exist: {source_root}")

    files: list[Path] = []
    for year_dir in sorted(
        (item for item in source_root.iterdir() if item.is_dir() and item.name.isdigit()),
        key=lambda item: int(item.name),
    ):
        year = int(year_dir.name)
        if year < start_year or year > end_year:
            continue
        for csv_file in sorted(year_dir.glob("*.csv")):
            files.append(csv_file.resolve())
            if limit is not None and len(files) >= limit:
                return files
    return files


def resolve_import_files(
    source_root: Path,
    start_year: int,
    end_year: int,
    *,
    limit: int | None = None,
    single_file: Path | None = None,
) -> list[Path]:
    if single_file is None:
        return collect_source_files(
            source_root=source_root,
            start_year=start_year,
            end_year=end_year,
            limit=limit,
        )

    resolved = single_file.expanduser().resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"CSV file does not exist: {single_file}")
    if not resolved.is_file():
        raise ValueError(f"CSV import path must be a file: {single_file}")
    if resolved.suffix.lower() != ".csv":
        raise ValueError(f"CSV import path must end with .csv: {single_file}")
    return [resolved]


def detect_header_version(fieldnames: Sequence[str | None]) -> str:
    normalized = {_normalize_header_name(name) for name in fieldnames if name}
    for version, mapping in HEADER_MAPPINGS.items():
        if all(any(alias in normalized for alias in aliases) for aliases in mapping.values()):
            return version
    header_preview = ", ".join(sorted(normalized))
    raise ValueError(f"Unsupported CSV header: {header_preview}")


def normalize_csv_row(
    row: Mapping[str, str | None],
    *,
    header_version: str,
    row_num: int,
    file_path: Path,
    file_date: date,
    data_source: str,
) -> CanonicalRow:
    if header_version not in HEADER_MAPPINGS:
        raise ValueError(f"Unsupported header version: {header_version}")

    normalized_row = {
        _normalize_header_name(key): (value.strip() if value is not None else "")
        for key, value in row.items()
        if key is not None
    }
    mapping = HEADER_MAPPINGS[header_version]

    raw_code = _get_required_value(normalized_row, mapping["code"], "code", row_num, file_path)
    normalized_code = _normalize_import_code(raw_code)
    if not normalized_code:
        raise ValueError(f"{file_path}:{row_num} has an unsupported stock code: {raw_code}")

    name = _get_optional_value(normalized_row, mapping["name"]) or normalized_code
    trade_date = _parse_trade_date(
        _get_required_value(normalized_row, mapping["date"], "date", row_num, file_path),
        file_path=file_path,
        row_num=row_num,
    )
    if trade_date != file_date:
        raise ValueError(
            f"{file_path}:{row_num} has trade date {trade_date.isoformat()} "
            f"that does not match file date {file_date.isoformat()}"
        )

    return CanonicalRow(
        file_path=str(file_path.resolve()),
        row_num=row_num,
        code=normalized_code,
        name=name[:50],
        trade_date=trade_date,
        open_price=_parse_float(_get_optional_value(normalized_row, mapping["open"])),
        high_price=_parse_float(_get_optional_value(normalized_row, mapping["high"])),
        low_price=_parse_float(_get_optional_value(normalized_row, mapping["low"])),
        close_price=_parse_float(_get_optional_value(normalized_row, mapping["close"])),
        volume=_parse_float(_get_optional_value(normalized_row, mapping["volume"])),
        amount=_parse_float(_get_optional_value(normalized_row, mapping["amount"])),
        pct_chg=_parse_float(_get_optional_value(normalized_row, mapping["pct_chg"])),
        data_source=data_source,
    )


def load_pre_insert_hook(hook_path: str | None) -> PreInsertHook | None:
    if not hook_path:
        return None

    module_name, separator, attribute_name = hook_path.partition(":")
    module_name = module_name.strip()
    attribute_name = attribute_name.strip()
    if not separator or not module_name or not attribute_name:
        raise ValueError("Pre-insert hook must use the format `module:function`.")

    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise ValueError(f"Unable to import hook module `{module_name}`.") from exc

    try:
        hook = getattr(module, attribute_name)
    except AttributeError as exc:
        raise ValueError(f"Hook module `{module_name}` does not define `{attribute_name}`.") from exc

    if not callable(hook):
        raise TypeError(f"Pre-insert hook `{hook_path}` must be callable.")
    return hook


def apply_pre_insert_hook(
    row: CanonicalRow,
    *,
    hook: PreInsertHook | None,
    context: PreInsertHookContext,
) -> CanonicalRow | None:
    if hook is None:
        return row

    transformed = hook(row, context)
    if transformed is None:
        return None
    if not isinstance(transformed, CanonicalRow):
        raise TypeError("Pre-insert hook must return `CanonicalRow` or `None`.")
    return transformed


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    _configure_logging(args.log_level)
    pre_insert_hook = load_pre_insert_hook(args.pre_insert_hook)

    files = resolve_import_files(
        source_root=args.source_root,
        start_year=args.start_year,
        end_year=args.end_year,
        limit=args.limit_files,
        single_file=args.file,
    )
    if not files:
        LOGGER.warning("No CSV files found under %s for years %s-%s.", args.source_root, args.start_year, args.end_year)
        return 0

    if args.file:
        LOGGER.info("Collected 1 CSV file from explicit path: %s", files[0])
    else:
        LOGGER.info(
            "Collected %s CSV files from %s (%s-%s).",
            len(files),
            args.source_root,
            args.start_year,
            args.end_year,
        )
    if args.pre_insert_hook:
        LOGGER.info("Loaded pre-insert hook: %s", args.pre_insert_hook)

    if args.dry_run:
        _run_dry_run(
            files=files,
            batch_size=args.batch_size,
            data_source=args.data_source,
            pre_insert_hook=pre_insert_hook,
        )
        return 0

    _ensure_psycopg_available()
    dsn = build_psycopg_dsn(get_config().get_db_url())

    failed_files = 0
    processed_files = 0
    skipped_files = 0
    imported_rows = 0

    with connect_import_db(dsn) as conn:
        with conn.transaction():
            _ensure_support_tables(conn)
        initial_target_rows = _get_stock_daily_row_count(conn)

        for file_path in files:
            try:
                result = _process_file(
                    conn=conn,
                    file_path=file_path,
                    batch_size=args.batch_size,
                    data_source=args.data_source,
                    pre_insert_hook=pre_insert_hook,
                    reprocess=args.reprocess,
                )
            except Exception as exc:
                failed_files += 1
                LOGGER.exception("Failed to process %s: %s", file_path, exc)
                if not args.continue_on_error:
                    break
                continue

            if result.skipped:
                skipped_files += 1
                LOGGER.info("Skipped already completed file: %s (use --reprocess to import it again)", file_path)
                continue

            processed_files += 1
            imported_rows += result.row_count
            LOGGER.info(
                "Imported %s rows from %s using header %s.",
                result.row_count,
                file_path.name,
                result.header_version,
            )

        pending_ma_refresh = _count_pending_ma_refresh(conn)
        if pending_ma_refresh and not args.skip_ma_backfill:
            LOGGER.info("Refreshing MA columns for all pending files (%s manifest rows).", pending_ma_refresh)
            with conn.transaction():
                _backfill_moving_averages(conn)
                _clear_pending_ma_refresh(conn)
        elif pending_ma_refresh:
            LOGGER.warning(
                "Skipping MA backfill even though %s manifest rows are pending.",
                pending_ma_refresh,
            )

        _validate_import(conn, initial_target_rows=initial_target_rows)

    LOGGER.info(
        "Finished import. processed=%s skipped=%s failed=%s imported_rows=%s",
        processed_files,
        skipped_files,
        failed_files,
        imported_rows,
    )
    return 1 if failed_files else 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import historical stock daily CSV files into PostgreSQL with staging, upsert, and MA backfill.",
    )
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT, help="Root directory of year-partitioned CSV files.")
    parser.add_argument("--start-year", type=int, default=2000, help="Inclusive start year.")
    parser.add_argument("--end-year", type=int, default=datetime.now().year, help="Inclusive end year.")
    parser.add_argument("--limit-files", type=int, default=None, help="Process only the first N files after sorting.")
    parser.add_argument("--file", type=Path, default=None, help="Import exactly one CSV file instead of scanning year directories.")
    parser.add_argument("--batch-size", type=int, default=5000, help="COPY batch size per file.")
    parser.add_argument("--data-source", default=DEFAULT_DATA_SOURCE, help="Value written to stock_daily.data_source.")
    parser.add_argument(
        "--pre-insert-hook",
        default=None,
        help="Optional hook in `module:function` format. Called for each normalized row before staging.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse files and validate rows without writing to the database.")
    parser.add_argument("--reprocess", action="store_true", help="Re-import files even if manifest status is already completed.")
    parser.add_argument("--skip-ma-backfill", action="store_true", help="Do not backfill ma5/ma10/ma20 after import.")
    parser.add_argument("--continue-on-error", action="store_true", help="Keep processing the remaining files after a file fails.")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Console log level.",
    )
    return parser


def _configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def _ensure_psycopg_available() -> None:
    if psycopg is None:
        raise RuntimeError("psycopg is required for database import. Install it with `pip install psycopg[binary]`.")


def connect_import_db(dsn: str):
    _ensure_psycopg_available()
    return psycopg.connect(dsn, autocommit=True)


def _run_dry_run(
    files: Sequence[Path],
    *,
    batch_size: int,
    data_source: str,
    pre_insert_hook: PreInsertHook | None,
) -> None:
    total_source_rows = 0
    total_staged_rows = 0
    header_versions: dict[str, int] = {}
    for file_path in files:
        encoding, header_version = _detect_file_encoding_and_header(file_path)
        source_row_count = 0
        staged_row_count = 0
        for batch in _iter_canonical_batches(
            file_path=file_path,
            encoding=encoding,
            header_version=header_version,
            batch_size=batch_size,
            data_source=data_source,
            pre_insert_hook=pre_insert_hook,
        ):
            source_row_count += batch.source_row_count
            staged_row_count += batch.staged_row_count
        header_versions[header_version] = header_versions.get(header_version, 0) + 1
        total_source_rows += source_row_count
        total_staged_rows += staged_row_count
        LOGGER.info(
            "Validated %s staged rows (%s source rows) from %s using header %s.",
            staged_row_count,
            source_row_count,
            file_path.name,
            header_version,
        )
    LOGGER.info(
        "Dry run summary: files=%s source_rows=%s staged_rows=%s headers=%s",
        len(files),
        total_source_rows,
        total_staged_rows,
        header_versions,
    )


def _process_file(
    conn,
    *,
    file_path: Path,
    batch_size: int,
    data_source: str,
    pre_insert_hook: PreInsertHook | None,
    reprocess: bool,
) -> FileProcessResult:
    manifest_status = _get_manifest_status(conn, file_path)
    if manifest_status == "completed" and not reprocess:
        return FileProcessResult(
            file_path=file_path,
            header_version="unknown",
            source_row_count=0,
            staged_row_count=0,
            skipped=True,
        )

    file_date = _parse_file_date(file_path)
    file_year = _resolve_file_year(file_path, file_date)
    encoding, header_version = _detect_file_encoding_and_header(file_path)

    with conn.transaction():
        _mark_manifest_started(
            conn=conn,
            file_path=file_path,
            file_date=file_date,
            file_year=file_year,
            header_version=header_version,
        )

    source_row_count = 0
    staged_row_count = 0
    try:
        with conn.transaction():
            _delete_stage_rows(conn, file_path)
            for batch in _iter_canonical_batches(
                file_path=file_path,
                encoding=encoding,
                header_version=header_version,
                batch_size=batch_size,
                data_source=data_source,
                pre_insert_hook=pre_insert_hook,
            ):
                _copy_stage_rows(conn, batch.rows)
                source_row_count += batch.source_row_count
                staged_row_count += batch.staged_row_count
            _merge_stage_rows(conn, file_path)
            _delete_stage_rows(conn, file_path)
            _mark_manifest_completed(
                conn=conn,
                file_path=file_path,
                header_version=header_version,
                source_row_count=source_row_count,
                staged_row_count=staged_row_count,
            )
    except Exception as exc:
        with conn.transaction():
            _delete_stage_rows(conn, file_path)
            _mark_manifest_failed(conn, file_path=file_path, error_message=str(exc))
        raise

    return FileProcessResult(
        file_path=file_path,
        header_version=header_version,
        source_row_count=source_row_count,
        staged_row_count=staged_row_count,
        skipped=False,
    )


def _detect_file_encoding_and_header(file_path: Path) -> tuple[str, str]:
    last_error: Exception | None = None
    for encoding in SUPPORTED_ENCODINGS:
        try:
            with file_path.open("r", encoding=encoding, newline="") as handle:
                reader = csv.reader(handle)
                header = next(reader, None)
            if header is None:
                raise ValueError("CSV file is empty.")
            return encoding, detect_header_version(header)
        except (UnicodeDecodeError, ValueError) as exc:
            last_error = exc
    raise ValueError(f"Unable to decode or recognize header for {file_path}: {last_error}")


def _iter_canonical_batches(
    *,
    file_path: Path,
    encoding: str,
    header_version: str,
    batch_size: int,
    data_source: str,
    pre_insert_hook: PreInsertHook | None,
) -> Iterable[CanonicalBatch]:
    file_date = _parse_file_date(file_path)
    hook_context = PreInsertHookContext(
        file_path=file_path,
        file_date=file_date,
        header_version=header_version,
        data_source=data_source,
    )
    batch: list[CanonicalRow] = []
    source_row_count = 0
    with file_path.open("r", encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV file has no header row: {file_path}")
        for row_num, row in enumerate(reader, start=2):
            if _is_empty_row(row):
                continue
            source_row_count += 1
            normalized_row = normalize_csv_row(
                row=row,
                header_version=header_version,
                row_num=row_num,
                file_path=file_path,
                file_date=file_date,
                data_source=data_source,
            )
            transformed_row = apply_pre_insert_hook(
                normalized_row,
                hook=pre_insert_hook,
                context=hook_context,
            )
            if transformed_row is not None:
                batch.append(transformed_row)
            if source_row_count >= batch_size:
                yield CanonicalBatch(rows=batch, source_row_count=source_row_count)
                batch = []
                source_row_count = 0
    if source_row_count:
        yield CanonicalBatch(rows=batch, source_row_count=source_row_count)


def _ensure_support_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.stock_daily_stage (
                file_path TEXT NOT NULL,
                row_num INTEGER NOT NULL,
                code VARCHAR(10) NOT NULL,
                name VARCHAR(50) NOT NULL,
                trade_date DATE NOT NULL,
                open DOUBLE PRECISION,
                high DOUBLE PRECISION,
                low DOUBLE PRECISION,
                close DOUBLE PRECISION,
                volume DOUBLE PRECISION,
                amount DOUBLE PRECISION,
                pct_chg DOUBLE PRECISION,
                data_source VARCHAR(50) NOT NULL,
                imported_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
                PRIMARY KEY (file_path, row_num)
            );
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_stock_daily_stage_code_date
            ON public.stock_daily_stage (code, trade_date);
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_stock_daily_stage_file_path
            ON public.stock_daily_stage (file_path);
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.stock_daily_import_manifest (
                file_path TEXT PRIMARY KEY,
                file_name TEXT NOT NULL,
                file_date DATE NOT NULL,
                year INTEGER NOT NULL,
                header_version VARCHAR(16),
                status VARCHAR(16) NOT NULL,
                source_row_count INTEGER NOT NULL DEFAULT 0,
                staged_row_count INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                ma_backfill_pending BOOLEAN NOT NULL DEFAULT FALSE,
                started_at TIMESTAMP WITHOUT TIME ZONE,
                finished_at TIMESTAMP WITHOUT TIME ZONE,
                updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
            );
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_stock_daily_import_manifest_status
            ON public.stock_daily_import_manifest (status);
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_stock_daily_import_manifest_year
            ON public.stock_daily_import_manifest (year);
            """
        )


def _get_manifest_status(conn, file_path: Path) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT status
            FROM public.stock_daily_import_manifest
            WHERE file_path = %s
            """,
            (str(file_path.resolve()),),
        )
        row = cur.fetchone()
    return row[0] if row else None


def _mark_manifest_started(
    conn,
    *,
    file_path: Path,
    file_date: date,
    file_year: int,
    header_version: str,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.stock_daily_import_manifest (
                file_path,
                file_name,
                file_date,
                year,
                header_version,
                status,
                source_row_count,
                staged_row_count,
                error_message,
                ma_backfill_pending,
                started_at,
                finished_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, 'processing', 0, 0, NULL, FALSE, NOW(), NULL, NOW())
            ON CONFLICT (file_path) DO UPDATE
            SET
                file_name = EXCLUDED.file_name,
                file_date = EXCLUDED.file_date,
                year = EXCLUDED.year,
                header_version = EXCLUDED.header_version,
                status = 'processing',
                source_row_count = 0,
                staged_row_count = 0,
                error_message = NULL,
                started_at = NOW(),
                finished_at = NULL,
                updated_at = NOW();
            """,
            (str(file_path.resolve()), file_path.name, file_date, file_year, header_version),
        )


def _mark_manifest_completed(
    conn,
    *,
    file_path: Path,
    header_version: str,
    source_row_count: int,
    staged_row_count: int,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE public.stock_daily_import_manifest
            SET
                header_version = %s,
                status = 'completed',
                source_row_count = %s,
                staged_row_count = %s,
                error_message = NULL,
                ma_backfill_pending = TRUE,
                finished_at = NOW(),
                updated_at = NOW()
            WHERE file_path = %s
            """,
            (header_version, source_row_count, staged_row_count, str(file_path.resolve())),
        )


def _mark_manifest_failed(conn, *, file_path: Path, error_message: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE public.stock_daily_import_manifest
            SET
                status = 'failed',
                error_message = %s,
                finished_at = NOW(),
                updated_at = NOW()
            WHERE file_path = %s
            """,
            (error_message[:4000], str(file_path.resolve())),
        )


def _copy_stage_rows(conn, rows: Sequence[CanonicalRow]) -> None:
    if not rows:
        return
    with conn.cursor() as cur:
        with cur.copy(
            """
            COPY public.stock_daily_stage (
                file_path,
                row_num,
                code,
                name,
                trade_date,
                open,
                high,
                low,
                close,
                volume,
                amount,
                pct_chg,
                data_source
            ) FROM STDIN
            """
        ) as copy:
            for row in rows:
                copy.write_row(row.to_stage_tuple())


def _merge_stage_rows(conn, file_path: Path) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH deduped AS (
                SELECT DISTINCT ON (code, trade_date)
                    code,
                    name,
                    trade_date,
                    open,
                    high,
                    low,
                    close,
                    volume,
                    amount,
                    pct_chg,
                    data_source
                FROM public.stock_daily_stage
                WHERE file_path = %s
                ORDER BY code, trade_date, row_num DESC
            )
            INSERT INTO public.stock_daily (
                code,
                name,
                date,
                open,
                high,
                low,
                close,
                volume,
                amount,
                pct_chg,
                ma5,
                ma10,
                ma20,
                volume_ratio,
                data_source,
                created_at,
                updated_at
            )
            SELECT
                code,
                name,
                trade_date,
                open,
                high,
                low,
                close,
                volume,
                amount,
                pct_chg,
                NULL,
                NULL,
                NULL,
                NULL,
                data_source,
                NOW(),
                NOW()
            FROM deduped
            ON CONFLICT (code, date) DO UPDATE
            SET
                name = EXCLUDED.name,
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                amount = EXCLUDED.amount,
                pct_chg = EXCLUDED.pct_chg,
                data_source = EXCLUDED.data_source,
                updated_at = NOW();
            """,
            (str(file_path.resolve()),),
        )


def _delete_stage_rows(conn, file_path: Path) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM public.stock_daily_stage WHERE file_path = %s",
            (str(file_path.resolve()),),
        )


def _count_pending_ma_refresh(conn) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*)
            FROM public.stock_daily_import_manifest
            WHERE status = 'completed' AND ma_backfill_pending = TRUE
            """
        )
        row = cur.fetchone()
    return int(row[0]) if row else 0


def _backfill_moving_averages(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH ma_values AS (
                SELECT
                    id,
                    CASE WHEN COUNT(close) OVER w5 = 5 THEN AVG(close) OVER w5 END AS ma5,
                    CASE WHEN COUNT(close) OVER w10 = 10 THEN AVG(close) OVER w10 END AS ma10,
                    CASE WHEN COUNT(close) OVER w20 = 20 THEN AVG(close) OVER w20 END AS ma20
                FROM public.stock_daily
                WINDOW
                    w5 AS (PARTITION BY code ORDER BY date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW),
                    w10 AS (PARTITION BY code ORDER BY date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW),
                    w20 AS (PARTITION BY code ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW)
            )
            UPDATE public.stock_daily AS target
            SET
                ma5 = ma_values.ma5,
                ma10 = ma_values.ma10,
                ma20 = ma_values.ma20,
                volume_ratio = NULL,
                updated_at = NOW()
            FROM ma_values
            WHERE target.id = ma_values.id;
            """
        )


def _clear_pending_ma_refresh(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE public.stock_daily_import_manifest
            SET
                ma_backfill_pending = FALSE,
                updated_at = NOW()
            WHERE status = 'completed' AND ma_backfill_pending = TRUE
            """
        )


def _validate_import(conn, *, initial_target_rows: int) -> None:
    duplicates = _query_scalar(
        conn,
        """
        SELECT COUNT(*)
        FROM (
            SELECT code, date
            FROM public.stock_daily
            GROUP BY code, date
            HAVING COUNT(*) > 1
        ) AS duplicate_pairs
        """,
    )
    if duplicates:
        raise RuntimeError(f"Validation failed: found {duplicates} duplicate (code, date) pairs in stock_daily.")

    total_rows = _get_stock_daily_row_count(conn)
    manifest_source_rows, manifest_staged_rows = _query_row(
        conn,
        """
        SELECT
            COALESCE(SUM(source_row_count), 0),
            COALESCE(SUM(staged_row_count), 0)
        FROM public.stock_daily_import_manifest
        WHERE status = 'completed'
        """,
    )
    min_date, max_date = _query_row(
        conn,
        "SELECT MIN(date), MAX(date) FROM public.stock_daily",
    )
    LOGGER.info(
        "Validation summary: stock_daily rows=%s manifest staged rows=%s manifest source rows=%s min_date=%s max_date=%s duplicates=%s",
        total_rows,
        manifest_staged_rows,
        manifest_source_rows,
        min_date,
        max_date,
        duplicates,
    )
    if initial_target_rows == 0 and total_rows != manifest_staged_rows:
        raise RuntimeError(
            f"Validation failed: expected {manifest_staged_rows} stock_daily rows from manifest, found {total_rows}."
        )


def _get_stock_daily_row_count(conn) -> int:
    return int(_query_scalar(conn, "SELECT COUNT(*) FROM public.stock_daily"))


def _query_scalar(conn, sql: str) -> int | float | str | None:
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()
    return row[0] if row else None


def _query_row(conn, sql: str) -> tuple[object, ...]:
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()
    return tuple(row) if row else tuple()


def _normalize_header_name(name: str) -> str:
    return str(name).replace("\ufeff", "").strip()


def _get_required_value(
    row: Mapping[str, str],
    aliases: Sequence[str],
    field_name: str,
    row_num: int,
    file_path: Path,
) -> str:
    value = _get_optional_value(row, aliases)
    if value:
        return value
    raise ValueError(f"{file_path}:{row_num} is missing required field `{field_name}`.")


def _get_optional_value(row: Mapping[str, str], aliases: Sequence[str]) -> str | None:
    for alias in aliases:
        value = row.get(_normalize_header_name(alias))
        if value is not None and value != "":
            return value
    return None


def _parse_trade_date(raw_value: str, *, file_path: Path, row_num: int) -> date:
    text = raw_value.strip()
    for pattern in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    raise ValueError(f"{file_path}:{row_num} has unsupported date format: {raw_value}")


def _parse_file_date(file_path: Path) -> date:
    try:
        return datetime.strptime(file_path.stem, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"File name is not a trade date: {file_path.name}") from exc


def _resolve_file_year(file_path: Path, file_date: date) -> int:
    if file_path.parent.name.isdigit():
        return int(file_path.parent.name)
    return file_date.year


def _parse_float(raw_value: str | None) -> float | None:
    if raw_value is None:
        return None
    text = raw_value.strip().replace(",", "").replace("%", "")
    if not text or text in {"--", "None", "none", "NaN", "nan"}:
        return None
    return float(text)


def _is_empty_row(row: Mapping[str, str | None]) -> bool:
    return not any((value or "").strip() for value in row.values())


def _normalize_import_code(raw_code: str) -> str | None:
    normalized = normalize_code(raw_code)
    if normalized:
        return normalized

    fallback = normalize_stock_code(raw_code).strip().upper()
    if fallback.isdigit() and len(fallback) in (5, 6):
        return fallback
    return None


if __name__ == "__main__":
    raise SystemExit(main())
