# Dispatch Plan ！ EDT-db-postgres-20260315-181513

**Session**: .workflow/.csv-wave/EDT-db-postgres-20260315-181513  
**Date**: 2026-03-15  
**Source**: Zhongshu approved plan + Menxia conditions

**Routing Rules Applied**
- Feature/architecture/code/refactor/implement/API -> gongbu (IMPL)
- Deploy/CI-CD/infrastructure/container/monitoring/security ops -> bingbu (OPS)
- Data analysis/statistics/cost/reports/resource mgmt -> hubu (DATA)
- Documentation/README/UI copy/specs/API docs -> libu (DOC)
- Testing/QA/bug/code review/compliance -> xingbu (QA)

**Menxia Conditions (must be satisfied)**
1. Specify PostgreSQL driver choice and OS package needs to avoid Docker build failures.
2. Add explicit handling for `DATABASE_PATH` used for auth data dir when PG enabled, or introduce `DATA_DIR`.
3. Include README update per repo guideline.

**Global Acceptance Criteria**
- Config returns PG URL when PG env is set, with `DATABASE_URL` override; SQLite fallback preserved.
- Requirements include PG driver; engine works in both SQLite and PG modes.
- Docker/compose passes PG envs and optional postgres service boots for local/dev.
- Migration steps include export/import and validation.
- Docs list POSTGRES_* vars and SQLite fallback, plus README update.
- Tests cover URL selection logic; PG smoke steps are documented.

**Driver Decision**
- Driver: `psycopg[binary]` (psycopg3) for `postgresql+psycopg` URLs.
- OS packages: none required when binary wheels are available; if base image lacks wheels, add `libpq-dev` and `gcc` to Dockerfile and document it.

**Batches And Dependencies**

**Batch 1 ！ Foundations (exec_mode: parallel)**
1. `IMPL-001 (gongbu)` ！ Depends on: none. Scope: Add POSTGRES_* config fields and `DATABASE_URL` override in `src/config.py`; build DB URL selection; keep SQLite fallback; only create local dirs for SQLite; explicit handling for `DATABASE_PATH`/`DATA_DIR` when PG enabled. Acceptance criteria: PG URL returned when envs set; SQLite fallback preserved; `DATABASE_PATH` not used to build PG URL and is still honored for auth data dir or replaced by documented `DATA_DIR`.
2. `IMPL-002 (gongbu)` ！ Depends on: IMPL-001. Scope: Add PG driver dependency; ensure `DatabaseManager` builds SQLAlchemy engine for both SQLite and PG. Acceptance criteria: Dependency list includes `psycopg[binary]`; SQLAlchemy URL uses `postgresql+psycopg`; engine creation succeeds for SQLite and PG; no SQLite-only assumptions in engine setup.

**Batch 2 ！ Runtime And Migration (exec_mode: parallel)**
1. `OPS-001 (bingbu)` ！ Depends on: IMPL-002. Scope: Update `docker/Dockerfile` and `docker/docker-compose.yml` to pass PG envs; add optional postgres service for local/dev. Acceptance criteria: Compose passes POSTGRES_* and optional `DATABASE_URL`; postgres service boots; Docker build succeeds without extra OS packages due to `psycopg[binary]` or adds `libpq-dev` + `gcc` if binary wheels are unavailable.
2. `DATA-001 (hubu)` ！ Depends on: IMPL-001, IMPL-002. Scope: Define migration path from SQLite to PG, including tooling and verification. Acceptance criteria: Step-by-step procedure includes export, import, and validation; includes data integrity checks (row counts or checksums) and rollback/backup guidance.

**Batch 3 ！ Documentation And QA (exec_mode: parallel)**
1. `DOC-001 (libu)` ！ Depends on: IMPL-001, IMPL-002, OPS-001, DATA-001. Scope: Update `.env.example` with PG placeholders; update deployment docs and README; update `docs/CHANGELOG.md`. Acceptance criteria: Docs list POSTGRES_HOST/PORT/DB/USER/PASSWORD and `DATABASE_URL`; README updated; migration procedure documented; changelog entry added.
2. `QA-001 (xingbu)` ！ Depends on: IMPL-001, IMPL-002. Scope: Add tests for DB URL selection logic; document PG smoke test steps. Acceptance criteria: Unit tests cover PG selection, SQLite fallback, and `DATABASE_URL` override; manual PG smoke steps are written and cross-referenced in docs.
