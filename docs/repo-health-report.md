## Repo Health Report
Date: 2026-10-12

## Summary
- CI signals are healthy: `make lint` and `make test` both exited 0 (Ruff: all checks passed).
- No production-looking secrets found in tracked sources; `.env` is gitignored and `.env.example` only contains documented local defaults (`postgres` / `local-dev-key`).
- Core route → service → repository call chain is respected for HTTP handlers; repositories own SQLAlchemy queries.
- Several standards gaps remain: services still take/pass `Session`, write-auth ignores `WRITE_API_KEY_HEADER`, Socrata client uses `GET` while agent standards ask for `POST`, and refresh/nearby domain rules live in routes.
- Test/contract coverage is strong for CRUD + refresh auth paths; gaps remain for circle-only geo validation, nearby success, CORS wiring, and production hardening (rate limits / security headers / RBAC).

## Checks Run
- make lint (exit=0)
- make test (exit=0)

## Findings (prioritized)

### P0 (must fix)
- None identified from static review + provided CI outputs. No accidental cloud credentials, private keys, or production API tokens found in tracked files.

### P1 (should fix)
- **`WRITE_API_KEY_HEADER` is dead config.** `settings.write_api_key_header` is read by tests/fixtures, but `require_write_auth` binds `Header(default="")` on param `x_api_key` (always `X-API-Key` / `x-api-key`). Changing `WRITE_API_KEY_HEADER` does not change what the API accepts.
  - Where: `app/api/dependencies.py`, `app/settings.py`
- **Ingestion HTTP method diverges from repo standards.** Agent standards require SODA ingestion via `POST`; `SocrataClient._get` uses `httpx.get`. Align implementation or explicitly amend standards/docs if GET is intentional for this dataset.
  - Where: `app/clients/socrata_client.py`; standards in `AGENTS.md` / housing-api-agent-standards
- **Domain rules in route handlers.** `/refresh` source-identity validation and `/nearby` coordinate gating raise `HTTPException` in the route instead of typed domain errors (`ValidationError` / `NotFoundError`) from the service layer. Domain `ValidationError` in `app/core/errors.py` is unused.
  - Where: `app/api/routes/housing_units.py` (`refresh_housing_unit`, `get_nearby_housing_units`)
- **`CORS_ALLOWED_ORIGINS` is configured but never applied.** Settings expose CORS origins; `app/main.py` does not register `CORSMiddleware` (or equivalent). Browser clients relying on that env var will not get CORS headers.
  - Where: `app/settings.py`, `app/main.py`
- **Production hardening called for by AGENTS still absent (accepted MVP debt, but still a standards gap):** no rate limiting/throttling, no security headers/CSP, no audit logging for writes, and no viewer/editor/admin RBAC (single shared write key only). README documents this as future work; AGENTS still lists roles + rate limiting as required.
- **Circle geo edge-case risk.** `_apply_circle_filter` divides by `cos(center_lat)`; latitudes near ±90° can zero/near-zero the denominator and blow up the longitude delta.
  - Where: `app/repositories/housing_unit_repository.py`
- **Contract coverage gaps vs geo standards:**
  - No dedicated contract test for `geo_shape=circle` with missing required params (`center_lat` / `center_lon` / `radius_m`) returning `422` + `{ code, message, details }`.
  - No nearby **success** contract (only missing-radius / no-coordinates negatives).
  - Where: `tests/contract/test_get_housing_units_contract.py`, `tests/contract/test_bonus_endpoints_contract.py`

### P2 (nice to have)
- **Service layer couples to SQLAlchemy `Session`.** Services do not run queries (good), but they import and thread `Session` through every function. Strict reading of “repositories are the only layer that may use SQLAlchemy sessions” still flags this; a unit-of-work / session-scoped repository wrapper would decouple services.
  - Where: `app/services/housing_unit_service.py`
- **Import CLI bypasses the service layer** and calls `housing_unit_repository` + `SessionLocal` directly; dry-run also calls private `client._fetch_page`. Prefer a service/import orchestration API and public client methods.
  - Where: `app/scripts/import_nyc_data.py`
- **`os.getenv` outside `app/settings.py` in e2e fixtures** (`E2E_BASE_URL` in `tests/e2e/conftest.py`). Prefer a settings field for test/runtime override to keep the env-read boundary intact.
- **Magic / duplicated pagination defaults** (`limit` default 100 / max 1000 on list; nearby default 10 / max 100) live as literals in route signatures rather than shared constants.
  - Where: `app/api/routes/housing_units.py`
- **ILIKE wildcard injection (soft).** `street_name` / `construction_type` filters interpolate user input into `%...%` patterns without escaping `%` / `_`, so callers can broaden matches unintentionally.
  - Where: `app/repositories/housing_unit_repository.py` (`_apply_filters`)
- **Alembic migrations are linear and have correct reverse ops**, but are not inherently re-runnable outside Alembic’s version table (normal). Downgrades for additive column/constraint revisions look correct; no data backfill/locking concerns in current revisions. Consider documenting that downgrade of `uq_housing_units_socrata_row_id` is safe only when no dependents exist (none today).
  - Where: `alembic/versions/20260421_*.py`, `20260423_*.py`, `20260424_*.py`
- **Test depth:** e2e coverage is thin (health + one CRUD lifecycle). Unit tests omit `count_housing_units`. Some negative nearby tests assert on message substrings rather than stable error codes alone.

## Suggested next actions
1. Wire `require_write_auth` to `settings.write_api_key_header` (FastAPI `Header(..., alias=...)`) so config and enforcement match; add a contract test with a custom header name.
2. Move refresh “has source identity” and nearby “has coordinates” checks into the service layer; raise `ValidationError` / `NotFoundError`; keep HTTP mapping only in routes.
3. Either switch Socrata ingestion to `POST` per standards, or update `AGENTS.md` / agent standards to document GET as the chosen SODA access mode.
4. Register CORS from `settings.cors_allowed_origins` (or remove the unused setting until needed).
5. Add contract tests: circle missing-param `422` + `INVALID_GEO_FILTER`; nearby success path + `X-Geo-Approximation` header.
6. Guard circle longitude delta when `cos(lat)` is near zero; add a unit/integration case near high latitudes.
7. Track hardening backlog explicitly (rate limit, security headers, audit logs, RBAC) so AGENTS “required” items do not silently drift from MVP scope.
