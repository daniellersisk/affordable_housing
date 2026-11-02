## Repo Health Report
Date: 2026-11-02

## Summary
- CI inputs are green: `make lint` exit 0 (Ruff: all checks passed) and `make test` exit 0.
- No accidental production secrets found in tracked sources; `.env` is gitignored and `.env.example` uses local placeholders only.
- Core CRUD/import/refresh flow is present with typed domain errors, centralized settings, and solid unit/integration/contract coverage for primary write/read paths.
- Standards gaps remain: services import/pass SQLAlchemy `Session`; `tests/e2e/conftest.py` calls `os.getenv`; `WRITE_API_KEY_HEADER` is not wired into the auth dependency; `CORS_ALLOWED_ORIGINS` is configured but unused.
- Production-readiness items called out in README/AGENTS (RBAC, rate limiting, security headers, PostGIS-quality geo) are still open.
- Alembic chain is linear with working downgrades; migrations are version-gated (not re-runnable SQL) and appropriate for current schema size.

## Checks Run
- make lint (exit=0)
- make test (exit=0)
- Static inspection only (no additional commands or test runs): architecture layering, env/secret usage, constants/enums, Alembic revisions, and test inventory.

## Findings (prioritized)
### P0 (must fix)
- None identified from CI results + static review. Lint/tests passed; no committed live credentials/tokens detected.

### P1 (should fix)
- **Auth header config drift:** `settings.write_api_key_header` / `WRITE_API_KEY_HEADER` is documented and used by test helpers, but `require_write_auth` binds `Header(default="")` on parameter `x_api_key` (always `X-API-Key`). Custom header names will not authenticate.
- **Non-constant-time API key compare:** `require_write_auth` uses `!=` instead of `hmac.compare_digest` / `secrets.compare_digest`, which is a weak pattern for secret comparison.
- **Layering — services own SQLAlchemy `Session`:** `app/services/housing_unit_service.py` imports `sqlalchemy.orm.Session` and threads sessions through every public function. AGENTS require services to call repositories only and not touch SQLAlchemy sessions/queries directly. Routes also import `Session` for `commit()` (acceptable as HTTP transaction boundary) but service coupling is the standards gap.
- **Business rules in route handlers:** refresh “no source identity → 422” and nearby “missing coordinates → 404” / filter assembly live in `app/api/routes/housing_units.py` instead of the service layer raising typed domain errors (`ValidationError` / `NotFoundError`). Domain `ValidationError` in `app/core/errors.py` is effectively unused.
- **Env reads outside settings:** `tests/e2e/conftest.py` calls `os.getenv("E2E_BASE_URL")`. AGENTS allow `os.getenv` only in `app/settings.py` (tests should still prefer settings or a test-only settings field).
- **Dead CORS config:** `CORS_ALLOWED_ORIGINS` is loaded in `app/settings.py` and documented in README, but `CORSMiddleware` is never registered in `app/main.py`.
- **Security / role model incomplete vs AGENTS:** single shared write key only; no viewer/editor/admin RBAC; no rate limiting/throttling; no security headers/CSP. README already marks these as remaining work — still a standards gap for “public API included” hardening.
- **Contract/geo success coverage gaps:** geo contract tests focus on 422 paths (missing/mixed shape). No contract success assertions for `geo_shape=rectangle` / `geo_shape=circle` happy-path response schema; nearby has failure tests but no success-path contract for `X-Geo-Approximation` + item schema. `count_housing_units` has no dedicated unit test. No unit tests for `require_write_auth`.

### P2 (nice to have)
- **Import ETL bypasses service:** `app/scripts/import_nyc_data.py` calls `housing_unit_repository` directly (and dry-run calls private `SocrataClient._fetch_page`). Prefer a service/facade for upsert orchestration and a public client method for one-page fetch.
- **Circle geo numerical edge:** bounding-box approximation divides by `cos(center_lat)`; latitudes near ±90 make `lon_delta` explode. Documented as approximation, but worth guarding/clamping.
- **Magic / duplicated pagination defaults:** `limit=100` / `le=1000` appear in route Query params and again as defaults in `HousingUnitFilters` — extract shared constants/enums.
- **Health endpoint observability:** `GET /health` has no structured request/success logging despite the “every endpoint” logging standard.
- **Geo query performance:** no indexes on `(latitude, longitude)` (or PostGIS); list/nearby geo filters will sequential-scan at import scale.
- **`num_units` filter vs create semantics:** create allows `num_units=0`, but list filters use `ge=1` for min/max — zero-unit rows are invisible to unit-range filters.
- **Migration notes:** three linear revisions (`39c99893cbde` → `b1f4c8e2a031` → `3f80c8906eca`) with coherent downgrades. Not SQL-idempotent if reapplied outside Alembic versioning (normal). `add_socrata_row_id` adds a unique constraint without a pre-check for duplicates (safe while values are NULL; would fail if duplicates already existed).
- **Stale `ConflictError` docstring** still mentions “source-managed row write attempts” though source-managed rows are intentionally writable.
- **Compose local defaults:** Postgres published on host `5432` with example password `postgres` — fine for local challenge, unsafe if this compose file is reused as a production deploy template.
- **E2E breadth:** one CRUD lifecycle + health scaffold; refresh/geo/alias paths rely on contract tests only (acceptable if contract suite grows the missing success cases).

## Suggested next actions
- Wire `Header(alias=settings.write_api_key_header)` (or equivalent) and compare keys with `secrets.compare_digest`.
- Move refresh/nearby domain checks into `housing_unit_service` (raise `ValidationError` / `NotFoundError`); keep HTTP mapping in routes only.
- Reduce service SQLAlchemy coupling (e.g. unit-of-work/session gateway owned above the service, or repository methods that do not require the service to type `Session`).
- Register CORS from `settings.cors_allowed_origins` or remove the unused setting/docs until implemented.
- Route `E2E_BASE_URL` through settings (or a test settings helper) so only `app/settings.py` reads the environment.
- Add contract tests for geo rectangle/circle success schemas, nearby success + `X-Geo-Approximation`, and unit tests for `count_housing_units` + `require_write_auth`.
- Schedule production hardening: rate limiting, security headers, audit fields for writes, and RBAC (or explicitly document a narrower accepted auth model in AGENTS/README in the same change set).
- Optional follow-ups: lat/lon index or PostGIS `ST_DWithin`, shared pagination constants, import-script service facade, clamp polar circle filters, health endpoint logging.
