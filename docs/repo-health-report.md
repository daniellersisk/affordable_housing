## Repo Health Report
Date: 2026-08-31

## Summary
- CI signals are healthy: `make lint` and `make test` both exited 0 (Ruff: all checks passed).
- No production-looking secrets found in tracked sources; `.env` is gitignored and matches local-dev placeholders from `.env.example`.
- HTTP layering is mostly correct (routes call services; services call repositories; routes do not import repositories), but the service layer is coupled to SQLAlchemy `Session` and some domain rules live in route handlers.
- Auth/write boundaries and contract coverage for core CRUD + geo validation + refresh look solid; gaps remain around nearby success, production hardening (rate limits, security headers, constant-time key compare), and unused CORS settings.
- Alembic chain is linear with coherent upgrades/downgrades; migrations are conventional (not IF NOT EXISTS–idempotent) and look safe for clean apply/rollback.

## Checks Run
- make lint (exit=0)
- make test (exit=0)

## Findings (prioritized)
### P0 (must fix)
- None identified from static inspection + provided CI outputs. No hardcoded cloud credentials, private keys, or live tokens detected in application/source files. Lint and tests are green.

### P1 (should fix)
- **Service ↔ SQLAlchemy coupling:** `app/services/housing_unit_service.py` imports `sqlalchemy.orm.Session` and threads sessions through every public method. Standards require repositories as the only SQLAlchemy-touching layer; prefer a session/UoW abstraction or repository-owned session so services stay pure domain logic.
- **Domain rules in route handlers:** Refresh “no source identity → 422” and nearby geo composition (coordinate check, self-exclusion, approximation header) live in `app/api/routes/housing_units.py` instead of the service layer. That blurs error ownership and makes unit-testing those rules harder without FastAPI.
- **Non-constant-time API key compare:** `require_write_auth` uses `!=` against `settings.write_api_key`. Prefer `hmac.compare_digest` (after normalizing to equal-length / encoded bytes) to reduce timing-leak risk.
- **Production hardening gaps vs AGENTS/README:** no rate limiting/throttling, no security headers/CSP middleware, no write audit trail beyond structured request logs, and no viewer/editor/admin RBAC (single shared write key only — documented as intentional for challenge scope, but still below the stated minimum role model for production).
- **CORS config unused:** `CORS_ALLOWED_ORIGINS` is loaded in `app/settings.py` but `CORSMiddleware` is never registered in `app/main.py`, so the setting has no effect.
- **Magic pagination defaults:** list/nearby defaults (`limit=100`, `le=1000`, nearby `limit=10`) are inline literals rather than named constants in `app/core/constants.py`.
- **Env-var access outside settings:** `tests/e2e/conftest.py` calls `os.getenv("E2E_BASE_URL")` directly. Prefer extending `Settings` (or a test-only settings helper) so env reads stay centralized.
- **Test gap — nearby success path:** contract coverage exercises nearby 404 (no coordinates) and 422 (missing radius) but not a success case with coordinates, `X-Geo-Approximation` header, or self-exclusion behavior.
- **Test gap — list geo success contracts:** rectangle/circle validation failures are covered; happy-path list filtering by `geo_shape=rectangle|circle` is mainly integration-level, with thin/no dedicated HTTP contract assertions for successful geo responses.
- **Import dry-run uses private client API:** `app/scripts/import_nyc_data.py` calls `client._fetch_page(...)`, which can break silently if the client’s private surface changes; expose a public “first page / preview” method instead.
- **Repository raises domain errors:** `ConflictError` / `NotFoundError` originate in the repository as well as the service. Acceptable if intentional, but it duplicates not-found checks on update/delete (service then repo) and softens the “services raise typed domain errors” boundary.

### P2 (nice to have)
- **Alembic idempotence:** revisions `39c99893cbde` → `b1f4c8e2a031` → `3f80c8906eca` have correct downgrades (drop indexes/constraints/columns/table in reverse order). They are not re-runnable with `IF NOT EXISTS` guards (normal for Alembic). First migration still contains auto-generated “please adjust” comments.
- **Nearby `Response` injection anti-pattern:** `response: Response = None  # type: ignore[assignment]` is fragile; prefer `Response` via `Depends`/injection without a `None` default.
- **CLI import bypasses service layer:** bulk import talks to the repository directly. Fine for an ETL entrypoint, but a thin service/use-case wrapper would keep upsert rules in one place.
- **Stale ConflictError docstring:** `app/core/errors.py` still mentions “source-managed row write attempts,” which no longer matches the “source rows are editable” policy.
- **`.env.example` local secrets:** `WRITE_API_KEY=local-dev-key` and `POSTGRES_PASSWORD=postgres` are intentional placeholders; ensure shared/staging deployments never reuse them.
- **Circle filter approximation:** documented bounding-box approximation is an accepted MVP trade-off; production path (PostGIS `ST_DWithin`) remains future work.
- **Upsert does not delete removed upstream rows:** documented trade-off; callers should not assume DB ⊆ Socrata after import.

## Suggested next actions
1. Move nearby + refresh validation into `housing_unit_service` (raise typed `ValidationError` / `NotFoundError`); keep routes as thin HTTP adapters.
2. Decouple services from SQLAlchemy `Session` (repository facade or unit-of-work) and add/adjust unit tests accordingly.
3. Harden write auth with `hmac.compare_digest`; wire `CORSMiddleware` from `settings.cors_allowed_origins`; plan rate limits + security headers + write audit logging for production.
4. Add contract tests: nearby success (coords + header + self-exclusion); optional GET list success for rectangle/circle filters.
5. Promote pagination/limit defaults to constants; replace `client._fetch_page` with a public preview API; route `E2E_BASE_URL` through settings.
6. Keep migrations as-is for correctness; only add idempotent guards if you adopt a non-Alembic re-apply strategy (not required for current Compose/`alembic upgrade head` flow).
