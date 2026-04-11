# IMPL_PLAN

Goal: Validate PostgreSQL configuration via .env and ensure runtime/test pass.

Steps:
1. L0: Syntax check (py_compile) for config/auth modules.
2. L1: Execute DB URL selection tests.
3. L2: Runtime smoke check using DatabaseManager (reads .env).

Success:
- Tests pass
- Smoke check passes without exposing secrets
