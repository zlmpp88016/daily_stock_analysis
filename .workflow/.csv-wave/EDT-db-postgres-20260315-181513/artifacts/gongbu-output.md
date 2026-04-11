## IMPL-001 (gongbu) - 2026-03-15
Summary of changes:
- Added PostgreSQL env/config fields plus DATABASE_URL override.
- Updated DB URL selection to prefer DATABASE_URL, then PostgreSQL, then SQLite.
- SQLite remains the only case that creates local data directories.
- Added DATA_DIR override for auth storage with DATABASE_PATH fallback.

Files touched:
- src/config.py
- src/auth.py

Assumptions:
- Use PostgreSQL only when POSTGRES_HOST, POSTGRES_DB, and POSTGRES_USER are all non-empty.
- POSTGRES_PORT defaults to 5432 when unset or empty.

Update:
- DATABASE_URL with scheme postgres/postgresql is rewritten to postgresql+psycopg for driver compatibility.

## IMPL-002 (gongbu) - 2026-03-15
Summary of changes:
- Added PostgreSQL driver dependency to requirements.

Files touched:
- requirements.txt

Assumptions:
- Use psycopg[binary] to avoid extra system dependencies where wheels are available.
