## Repo Health Report
Date: 2026-10-19

## Summary
- CI signals are healthy: `make lint` and `make test` both exited 0 (ruff: all checks passed).
- Architecture largely follows route → service → repository; services avoid FastAPI/`HTTPException` and raise typed domain errors (`NotFoundError`, `ConflictError`).
- No production secrets found in tracked sources; `.env` is gitignored and `.env.example` only carries local placeholders (`WRITE_API_KEY=local-dev-key`, default Postgres credentials).
- Soft layering / production-hardening gaps remain: services take SQLAlchemy `Session`, nearby/refresh validation lives partly in routes, CORS/rate-limit/security headers and RBAC are not implemented (partly documented as out of challenge scope).
- Alembic chain is linear and downgrades reverse cleanly; migrations are Alembic-standard (not re-runnable DDL) with no data backfill hazards on the additive column migrations reviewed.
- Test suite is strong on CRUD/geo contracts; notable gaps are nearby success-path coverage, unused domain `ValidationError`, and thin e2e beyond CRUD lifecycle.

## Checks Run
- make lint (exit=0)
- make test (exit=0)

## Findings (prioritized)

### P0 (must fix)
- None identified from static inspection plus green lint/test CI. No hardcoded production credentials or layering breaks that would block merge of `main`.

### P1 (should fix)
- **Auth header config drift:** `settings.write_api_key_header` is used by tests when building headers, but `require_write_auth` binds `Header(default="")` on parameter `x_api_key` only. Changing `WRITE_API_KEY_HEADER` would not change the header FastAPI actually validates (`app/api/dependencies.py`).
- **API key comparison is not constant-time:** `x_api_key != settings.write_api_key` is susceptible to timing side channels; prefer `hmac.compare_digest` (or equivalent) for write-route auth.
- **`CORS_ALLOWED_ORIGINS` is unused:** settings expose CORS config, but `app/main.py` never registers `CORSMiddleware` (or equivalent). Either wire CORS from settings or drop the dead config to avoid a false sense of coverage.
- **Route-layer domain logic on nearby/refresh:** `get_nearby_housing_units` builds geo filters, excludes self, and raises `HTTPException` for missing coordinates; `refresh_housing_unit` validates source identity with `HTTPException` instead of service-raised `ValidationError`/`NotFoundError`. This blurs the “services own domain rules; routes only map errors” boundary (`AGENTS.md`).
- **Services depend on SQLAlchemy `Session`:** handlers pass `Session` into services which forward it to repositories. No queries live in services (good), but this still couples services to the ORM session type contrary to the strict “repositories only touch SQLAlchemy” wording.
- **Production hardening not present:** no rate limiting/throttling, no security headers/CSP, no write audit trail beyond structured logs, and no viewer/editor/admin RBAC (single shared write key). README marks some of this as later scope; AGENTS still lists them as required security posture for a public API.
- **Bulk import bypasses the service layer:** `app/scripts/import_nyc_data.py` calls the repository directly. Acceptable for a CLI ETL, but it duplicates the sync path relative to `housing_unit_service.sync_from_source` and can drift.

### P2 (nice to have)
- **`os.getenv` outside settings in e2e:** `tests/e2e/conftest.py` reads `E2E_BASE_URL` via `os.getenv`; only `app/settings.py` should read env under project standards (tests are a common exception—still worth routing through settings or a dedicated test settings helper).
- **Domain `ValidationError` is unused:** defined in `app/core/errors.py` but never raised by services; refresh “no source identity” and similar cases are HTTP-mapped in routes instead.
- **Magic pagination defaults in routes:** `limit` default `100` / max `1000` (and nearby defaults) are inline rather than named constants/enums.
- **Nearby contract coverage is negative-only:** tests cover missing coords and missing `radius_m`, but not a success path with coordinates, `X-Geo-Approximation` header, or self-exclusion behavior (`tests/contract/test_bonus_endpoints_contract.py`).
- **Service unit coverage gap:** `count_housing_units` has no dedicated unit test (list/get/create/update/delete/sync are covered).
- **No migration downgrade / upgrade smoke tests:** Alembic revisions look correct by inspection (`39c99893cbde` → `b1f4c8e2a031` → `3f80c8906eca`), but there is no automated verify of upgrade/downgrade round-trip.
- **Geo circle filter is a bounding-box approximation:** documented and header-advertised; PostGIS `ST_DWithin` remains the accuracy upgrade path.
- **`API_AUTH_ENABLED=false` path:** auth bypass exists but has no contract/e2e assertion that write routes become open when disabled (risk of accidental misconfiguration in non-local envs is mitigated by settings `__post_init__` requiring a key when auth is on).

## Suggested next actions
1. Wire `require_write_auth` to `settings.write_api_key_header` and compare secrets with `hmac.compare_digest`.
2. Move nearby/refresh domain checks into `housing_unit_service` (raise `NotFoundError` / `ValidationError`); keep routes as thin mappers.
3. Apply CORS from `settings.cors_allowed_origins` in `app/main.py`, or remove the unused setting and document “no CORS” explicitly.
4. Add contract/e2e coverage for nearby success (coords present, approximation header, self excluded) and a unit test for `count_housing_units`.
5. When production readiness is in scope: rate limiting on public GETs, security headers, audit logging for writes, and role-separated keys (viewer/editor/admin) as already sketched in README/AGENTS.
6. Optionally introduce a thin import service façade used by both `/refresh` and `import_nyc_data` so upsert/normalization stays single-sourced above the repository.
