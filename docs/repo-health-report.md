## Repo Health Report
Date: 2026-11-23

## Summary
- CI signals are healthy: `make lint` and `make test` both exited 0 (Ruff: all checks passed).
- Core layering is mostly sound (routes call services; services call repositories; no FastAPI imports in services), with one clear exception: nearby/geo orchestration lives in the route handler.
- No production secrets appear committed; `.env` is gitignored and matches local-dev defaults from `.env.example` (`WRITE_API_KEY=local-dev-key`, empty `SODA_APP_TOKEN`).
- Config centralization is nearly complete; the only `os.getenv()` outside `app/settings.py` is in `tests/e2e/conftest.py` (`E2E_BASE_URL`).
- Alembic chain is linear and downgrades look correct; migrations are additive and not written for re-run idempotence (normal for Alembic).
- Highest-value follow-ups: move nearby logic into the service layer, close nearby/geo success contract gaps, and harden circle-filter edge cases / auth header config consistency.

## Checks Run
- make lint (exit=0)
- make test (exit=0)

## Findings (prioritized)

### P0 (must fix)
- None identified from static review plus green CI. No hardcoded production tokens/credentials found in tracked application source.

### P1 (should fix)
- **Layering: nearby business logic in route handler** (`app/api/routes/housing_units.py` `get_nearby_housing_units`). Coordinate presence checks, circle filter construction, self-exclusion, and result trimming belong in the service layer; routes should only parse input, call a service, and map errors.
- **Config standards violation:** `tests/e2e/conftest.py` calls `os.getenv("E2E_BASE_URL")` directly. Per AGENTS.md / settings rules, only `app/settings.py` may read env vars; add an optional settings field (or test-settings helper) and import it.
- **Auth header config drift:** `require_write_auth` always binds FastAPI `Header` as `x_api_key` and hardcodes `"X-API-Key"` in error details, while `settings.write_api_key_header` is configurable. Changing `WRITE_API_KEY_HEADER` would not change what the dependency actually reads.
- **Circle geo edge case:** `_apply_circle_filter` divides by `cos(center_lat)`. Schema allows `center_lat` of ±90, which yields division by zero / invalid lon delta. Guard extreme latitudes (or clamp) before computing `lon_delta`.
- **Nearby `Response` injection smell:** `response: Response = None  # type: ignore[assignment]` may skip setting `X-Geo-Approximation` depending on FastAPI injection behavior. Prefer a non-optional `Response` parameter (or `Response` via dependency) and assert the header in contract tests.
- **Test gaps (contract/e2e):**
  - No success-path contract for `GET /v1/housing-units/{id}/nearby` (only no-coords 404 and missing `radius_m` 422).
  - No HTTP success contracts for `geo_shape=rectangle` / `geo_shape=circle` list filtering (validation paths are covered; positive filter behavior relies on integration/unit only).
  - No dedicated contract for circle shape with missing required params (rectangle missing-params is covered).
- **Domain errors raised from repository:** `housing_unit_repository` raises `ConflictError` / `NotFoundError` directly. Standards prefer repositories surfacing persistence outcomes and services owning typed domain errors (current pattern works, but blurs the service boundary).

### P2 (nice to have)
- **Services import `sqlalchemy.orm.Session`:** Services do not execute queries (good), but they are coupled to SQLAlchemy session typing. A protocol/UoW or passing repo dependencies would better match “services never touch SQLAlchemy.”
- **Import script bypasses service layer:** `app/scripts/import_nyc_data.py` calls the repository directly. Acceptable for a CLI ETL, but inconsistent with the documented call chain; a thin service method would keep upsert rules in one place.
- **Magic numbers / strings:** Pagination defaults (`limit=100`, `le=1000`), geo header value `"bounding-box"`, and several auth field labels are inline rather than named constants/enums in `app/core/constants.py`.
- **Unused CORS settings:** `CORS_ALLOWED_ORIGINS` is loaded in settings but `CORSMiddleware` is never registered in `app/main.py`.
- **Documented-but-deferred production controls:** No rate limiting, security headers, audit logging for writes, or viewer/editor/admin RBAC. README correctly marks these as future; still worth tracking for production readiness.
- **Alembic idempotence:** Revisions `39c99893cbde` → `b1f4c8e2a031` → `3f80c8906eca` have correct upgrade/downgrade pairing and a clean linear history. They are not guarded with `IF NOT EXISTS` / conditional DDL (standard Alembic practice; fine unless operators re-apply outside Alembic).
- **Composite unique + NULLs:** `uq_housing_units_project_building` allows multiple rows where one/both of `project_id`/`building_id` are NULL (PostgreSQL NULL semantics). Intentional for manual creates, but worth documenting so partial source identities are not treated as unique.
- **List endpoint cost:** `list_housing_units` issues separate list + count queries per request (correct pagination UX; consider documenting or optimizing later).

## Suggested next actions
1. Extract `get_nearby_housing_units` domain logic into `housing_unit_service` (typed `NotFoundError` / validation), keep the route thin, and add a success contract asserting items schema + `X-Geo-Approximation`.
2. Route `E2E_BASE_URL` through `settings`; wire `require_write_auth` to `settings.write_api_key_header` (or stop advertising the header as configurable).
3. Add contract tests for successful rectangle/circle list filters and circle missing-param `422` / `INVALID_GEO_FILTER`.
4. Guard circle filter against `|lat| ≈ 90` (and add a unit test).
5. Optionally introduce pagination/geo/auth header constants; either wire CORS middleware or remove unused `CORS_ALLOWED_ORIGINS` until needed.
6. Keep RBAC / rate limits / security headers as an explicit production-hardening epic (already scoped in README), not as silent MVP debt.
