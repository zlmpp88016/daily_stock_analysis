# SQLite to PostgreSQL Migration

This guide describes a minimal, repeatable way to migrate data from the existing SQLite database to PostgreSQL.

## Preconditions
- Ensure PostgreSQL is running and reachable.
- Configure the application to use PostgreSQL via `DATABASE_URL` or `POSTGRES_*` env vars.
- Back up your SQLite database file before migrating.

## Recommended Tool (pgloader)
`pgloader` handles type mapping and table creation automatically for most SQLite schemas.

1. Stop the application to avoid concurrent writes.
2. Back up the SQLite database file.
3. Run the migration:

```bash
pgloader sqlite:///absolute/path/to/stock_analysis.db \
  postgresql://USER:PASSWORD@HOST:PORT/DBNAME
```

4. Start the application in PostgreSQL mode and confirm it can read/write.

## Validation Checklist
- Compare row counts for key tables (old SQLite vs new PostgreSQL).
- Spot-check recent rows in critical tables.
- Verify the application starts without migration errors.
- Keep the SQLite backup until PostgreSQL is fully verified.

## PostgreSQL Smoke Test
1. Set `DATABASE_URL` or `POSTGRES_*` in `.env`.
2. Run a minimal connection check:

```bash
python -c "from src.storage import DatabaseManager; DatabaseManager()"
```

3. Confirm tables exist in PostgreSQL and the app logs show successful initialization.

## Rollback
- Stop the application.
- Switch back to SQLite by unsetting `DATABASE_URL` and `POSTGRES_*`.
- Restore the SQLite file from backup.
