# Execution Plan

## Edict Description
分析当前项目使用的数据库，考虑以最小代价将其全部替换为 PostgreSQL（尽可能少修改代码即可完成底层数据库替换），并且在 `.env` 文件中预留 PostgreSQL 的 host / username / password 配置项。要求：明确现有数据库使用点、最小替换路径、必要的配置与迁移注意事项。

## Technical Analysis
- Relevant modules:
  - `src/config.py`: `Config.database_path` + `Config.get_db_url()` currently always builds a SQLite URL from `DATABASE_PATH`.
  - `src/storage.py`: `DatabaseManager` creates SQLAlchemy engine via `config.get_db_url()` and `Base.metadata.create_all()`; this is the central connection switch point.
  - `src/auth.py`: derives `DATA_DIR` from `DATABASE_PATH` for admin auth secrets (non-DB storage).
  - `api/deps.py`, `src/core/pipeline.py`, repositories/services: consume `DatabaseManager` (no direct DB URL usage).
- Configuration & runtime:
  - `.env.example` and `docker/Dockerfile` expose `DATABASE_PATH`; `docker/docker-compose.yml` mounts `data/` and loads `.env`.
  - Docs mention SQLite and `DATABASE_PATH` (`docs/docker/zeabur-deployment.md`, `docs/CHANGELOG.md`).
- Tests:
  - Multiple tests set `DATABASE_PATH` for temporary SQLite DBs; some use in-memory SQLite via `sqlite:///:memory:`.

## Execution Strategy
Keep SQLAlchemy ORM models and data access code unchanged; introduce PostgreSQL configuration as a minimal extension in config loading and DB URL construction. Prefer a single new configuration switch path (e.g., `DATABASE_URL` override or `POSTGRES_*` env vars) while keeping SQLite fallback for tests and local runs. Add the PostgreSQL driver dependency and update container/deployment config plus docs. Provide a pragmatic migration path from existing SQLite files to PostgreSQL with validation steps; avoid schema/logic rewrites.

## Subtask List
| Department | Task ID | Subtask | Priority | Dependencies | Expected Output |
|------------|---------|---------|----------|-------------|-----------------|
| gongbu | IMPL-001 | Add PostgreSQL config fields and DB URL selection in `src/config.py` (e.g., `POSTGRES_HOST/PORT/DB/USER/PASSWORD` + optional `DATABASE_URL` override). Ensure SQLite fallback remains for tests, and only create local directories for SQLite. | P0 | None | Config can build PostgreSQL URL when env is set; SQLite fallback preserved. |
| gongbu | IMPL-002 | Add PostgreSQL driver dependency (`psycopg` or `psycopg2-binary`) and ensure `DatabaseManager` works with both SQLite and PostgreSQL without code changes to callers. | P0 | IMPL-001 | Requirements updated; engine creation succeeds in both modes. |
| bingbu | OPS-001 | Update container/runtime config: `docker/Dockerfile`, `docker/docker-compose.yml` to pass new `POSTGRES_*` or `DATABASE_URL` vars, optionally add a `postgres` service for local/dev and document volumes/network. | P1 | IMPL-001 | Containers can connect to PostgreSQL with env wiring; optional local PG service defined. |
| hubu | DATA-001 | Define migration procedure from SQLite to PostgreSQL (tooling choice + verification steps). Include guidance for schema init and data transfer. | P1 | IMPL-001 | Migration notes or script plan with row-count and spot-check validation steps. |
| libu | DOC-001 | Update `.env.example` with PostgreSQL placeholders (host/username/password + port/dbname/sslmode), and update deployment docs (`docs/DEPLOY_EN.md`, `docs/docker/zeabur-deployment.md`) plus `docs/CHANGELOG.md`. | P1 | IMPL-001 | Docs reflect PostgreSQL config and usage. |
| xingbu | QA-001 | Add tests for DB URL selection logic and smoke test instructions for PostgreSQL. Keep SQLite tests intact; add optional PG integration test plan if CI allows. | P1 | IMPL-001 | Test coverage for config/URL logic; documented manual PG verification steps. |

## Acceptance Criteria
- IMPL-001: With `POSTGRES_HOST/USER/PASSWORD` (and DB name/port) set, `Config.get_db_url()` returns a valid PostgreSQL URL; with no PG envs, it returns the existing SQLite URL and still creates the local directory.
- IMPL-002: Requirements include a PostgreSQL driver; `DatabaseManager` can connect using both SQLite and PostgreSQL URLs without code changes to callers.
- OPS-001: Docker/compose can pass PostgreSQL envs; optional `postgres` service boots and app connects using the same envs.
- DATA-001: Migration path includes clear steps for exporting from SQLite and importing into PostgreSQL, plus verification (row counts, spot-checks, and error handling).
- DOC-001: `.env.example` and deployment docs explicitly list `POSTGRES_HOST`, `POSTGRES_USER`, `POSTGRES_PASSWORD` (and required companion vars).
- QA-001: Unit tests cover URL selection; manual PG smoke test steps documented and repeatable.

## Risk Assessment
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Data migration errors or partial transfers | Med | High | Provide explicit migration steps with validation; recommend backups and row-count checks. |
| Driver choice incompatibility (`psycopg` vs `psycopg2-binary`) | Med | Med | Pick one driver and document; smoke test in container and local. |
| Hidden SQLite assumptions in tests or tooling | Med | Med | Keep SQLite fallback for tests; add PG-only tests as optional. |
| Auth data dir coupling to `DATABASE_PATH` | Low | Med | If moving to PG, keep `DATABASE_PATH` for data dir or introduce explicit `DATA_DIR` without breaking existing behavior. |

## Open Questions
1. `team-config.json` was not found at `C:/Users/zhu/.codex/skills/team-edict/specs/team-config.json`; confirm routing rules if they differ from default department mapping.
2. Preferred PostgreSQL driver: `psycopg` (v3) or `psycopg2-binary`?
3. Should SQLite remain as a fallback for tests/local runs, or must PostgreSQL become mandatory everywhere (including tests/CI)?
4. Is a migration script expected in-repo, or is a documented manual procedure sufficient?
