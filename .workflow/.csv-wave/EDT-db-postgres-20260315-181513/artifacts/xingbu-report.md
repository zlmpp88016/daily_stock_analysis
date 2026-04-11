## QA-001 (xingbu) - 2026-03-15
Summary of changes:
- Added unit tests for Config.get_db_url selection logic.
- Added PostgreSQL smoke test steps to migration guide.

Files touched:
- tests/test_config_db_url.py
- docs/migration-sqlite-to-postgres.md

Assumptions:
- Smoke test uses DatabaseManager initialization to validate connectivity.
