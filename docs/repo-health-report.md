## Repo Health Report
Date: 2026-09-07

## Summary
- CI signals are healthy: `make lint` and `make test` both exited `0` (ruff: all checks passed).
- No production secrets or private keys found in tracked sources; `.env` is gitignored and matches local-dev placeholders in `.env.example`.
- Core layering is mostly respected (routes call services; services do not import FastAPI/`HTTPException`), but services still take/import SQLAlchemy `Session`, and one test helper reads env vars outside `app/settings.py`.
- Alembic history is a clean linear chain with matching upgrade/downgrade pairs; no unsafe data backfills observed.
- Highest-risk functional gap: circle geo filtering can divide by zero near the poles (`cos(±90°) = 0`), turning valid requests into unhandled 500s.
- Auth/CORS config is partially wired (`WRITE_API_KEY_HEADER`, `CORS_ALLOWED_ORIGINS` exist in settings but are not fully enforced in the app layer).

## Checks Run
- make lint (exit=0)
- make test (exit=0)

## Findings (prioritized)
### P0 (must fix)
- **Circle geo filter can 500 on valid latitude extremes.** `_apply_circle_filter` in `app/repositories/housing_unit_repository.py` computes `lon_delta` as `radius_m / (_METERS_PER_DEGREE_LAT * math.cos(math.radians(center_lat)))`. `HousingUnitFilters` allows `center_lat` in `[-90, 90]`, so `center_lat=±90` (and nearby poles) yields `ZeroDivisionError` / extreme blow-ups. Same path is used by `GET /v1/housing-units/{id}/nearby`. Guard polar latitudes or clamp `cos` to a minimum epsilon and return a structured `422` when the approximation is unsafe.

### P1 (should fix)
- **Service layer couples to SQLAlchemy sessions.** `app/services/housing_unit_service.py` imports `sqlalchemy.orm.Session` and threads sessions through every public function. AGENTS standards require repositories to be the only layer that imports/uses SQLAlchemy sessions/ORM types. Prefer a unit-of-work / repository facade so services stay pure-Python and session-free.
- **`os.getenv` used outside settings.** `tests/e2e/conftest.py` calls `os.getenv("E2E_BASE_URL")` directly. Standards require env access only via `app/settings.py` (add an optional settings field and import it).
- **CORS config is dead.** `settings.cors_allowed_origins` is loaded from `CORS_ALLOWED_ORIGINS`, but `app/main.py` never installs `CORSMiddleware` (or any CORS handling). Either wire it or remove the unused setting to avoid a false sense of protection.
- **Configurable API-key header is ignored by auth dependency.** `require_write_auth` binds `Header(default="")` on parameter `x_api_key` (always `X-API-Key`) and hardcodes that name in the 401 payload, while tests/clients honor `settings.write_api_key_header`. Changing `WRITE_API_KEY_HEADER` would break auth consistency.
- **Refresh validation lives in the route, not the service.** `refresh_housing_unit` checks missing `project_id`/`building_id` and raises `HTTPException(422)` in the route. Domain `ValidationError` in `app/core/errors.py` is unused. Move source-identity validation into the service and map it in the route layer.
- **Geo success-path contract coverage is thin.** Contract tests cover geo validation failures well, but there is no contract assertion for successful `geo_shape=rectangle` / `geo_shape=circle` list responses, and nearby coverage is only negative (missing coords / missing radius)—no happy-path schema/header (`X-Geo-Approximation`) contract.

### P2 (nice to have)
- **RBAC / rate limiting / security headers are intentionally deferred** (documented in README as later hardening). AGENTS still lists viewer/editor/admin and rate limiting as minimum security posture for public APIs—track as explicit backlog, not silent scope drift.
- **Import CLI bypasses the service layer.** `app/scripts/import_nyc_data.py` opens `SessionLocal` and calls the repository directly. Acceptable for ETL, but document the exception or route through a service command for consistency.
- **Pagination / nearby defaults are duplicated magic numbers** (`limit=100`, `le=1000`, nearby `limit=10`) across route signatures and `HousingUnitFilters` instead of shared constants.
- **ILIKE filters embed raw user substrings** (`%{street_name}%`, construction_type). Parameterization prevents SQL injection, but callers can broaden matches with `%`/`_` wildcards; escape LIKE metacharacters if exact substring semantics are required.
- **Composite unique `(project_id, building_id)` allows duplicate partial-NULL identities** under PostgreSQL NULL semantics (multiple rows with one side NULL). Consider partial unique indexes if that should be forbidden.
- **Alembic migrations are correct but not re-runnable without version tracking** (normal Alembic behavior). Chain `39c99893cbde → b1f4c8e2a031 → 3f80c8906eca` has symmetric downgrades; `uq_housing_units_socrata_row_id` is added on a freshly created nullable column (safe). No `IF NOT EXISTS` / data backfill guards—fine for greenfield, weaker if migrations are ever applied out-of-band.

## Suggested next actions
1. Fix polar/near-polar circle math (clamp or reject) and add unit + contract tests for `center_lat=±90` and a nearby unit at extreme latitude.
2. Wire or delete CORS settings; make `require_write_auth` honor `settings.write_api_key_header`.
3. Move refresh source-identity checks into the service (`ValidationError`) and stop importing `Session` types in the service layer (session stays an opaque dependency or moves behind the repository).
4. Route `E2E_BASE_URL` through `settings`; add contract tests for successful rectangle/circle list filters and nearby success (including `X-Geo-Approximation`).
5. Keep RBAC, rate limiting, and security headers on the documented hardening roadmap; do not treat README “deferred” items as done.
