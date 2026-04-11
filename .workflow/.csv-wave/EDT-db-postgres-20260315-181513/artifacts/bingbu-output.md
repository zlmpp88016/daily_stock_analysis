## OPS-001 (bingbu) - 2026-03-15
Summary of changes:
- Documented optional PostgreSQL envs in Dockerfile.
- Added PostgreSQL env pass-through in docker-compose.
- Added optional postgres service with compose profile.

Files touched:
- docker/Dockerfile
- docker/docker-compose.yml

Assumptions:
- PostgreSQL service is optional and enabled via COMPOSE_PROFILES=postgres.
- App services read POSTGRES_* or DATABASE_URL via env_file/.env and compose environment.
