## Repo Health Report
Date: 2026-10-26

## Summary
- CI signals are green: `make lint` exit 0 (Ruff: all checks passed) and `make test` exit 0.
- No production secrets or private keys found in tracked sources; `.env` is gitignored and `.env.example` only carries local-dev placeholders (`WRITE_API_KEY=local-dev-key`, empty `SODA_APP_TOKEN`).
- Core architecture largely matches AGENTS.md: routes call services, repositories own SQLAlchemy, services raise typed domain errors (`NotFoundError` / `ConflictError`) without FastAPI imports, and only `app/settings.py` reads env in application code (with one test-fixture exception).
- Notable gaps: circle geo filter can `ZeroDivisionError` near the poles; `WRITE_API_KEY_HEADER` is not applied when reading the auth header; refresh/nearby domain rules live in the route layer; production hardening (rate limits, security headers, RBAC roles, CORS wiring) remains deferred as documented in README.
- Alembic history is a clean linear chain with matching downgrades; migrations are not re-run idempotent (normal for Alembic) and are appropriate for greenfield schema evolution.
- Test pyramid is strong on contract/unit/integration; thinner on nearby success-path coverage and e2e breadth (one CRUD lifecycle).

## Checks Run
- make lint (exit=0)
- make test (exit=0)
- Static inspection only (no local command execution by this review): secrets patterns, layering imports, settings/`os.getenv` usage, constants/enums, public type hints, Alembic revisions, test inventory

## Findings (prioritized)
### P0 (must fix)
- None identified. No committed production credentials; lint/tests green; auth boundary for writes is present and contract-tested.

### P1 (should fix)
- **Circle geo filter can crash at high latitudes.** `_apply_circle_filter` divides by `cos(center_lat)`. Latitude validation allows ±90°, where `cos` is 0 → `ZeroDivisionError` → unhandled 500 on the public list/nearby paths. Guard poles / clamp latitude, or reject extreme centers with a structured 422.
- **`WRITE_API_KEY_HEADER` is config theater.** `settings.write_api_key_header` is used when *sending* keys in tests, but `require_write_auth` always binds FastAPI’s default `X-Api-Key` via `Header()` on parameter `x_api_key` — custom header names from env will not be read. Wire `Header(alias=settings.write_api_key_header)` (or drop the setting).
- **API key comparison is not constant-time.** `x_api_key != settings.write_api_key` should use `secrets.compare_digest` (after normalizing empty/missing) to reduce timing leak risk on the public write surface.
- **Domain rules in the route layer.** Missing source identity for `/refresh` and missing coordinates for `/nearby` are enforced in `housing_units.py` with `HTTPException`, not via service + `app.core.errors.ValidationError` / `NotFoundError`. Moves business rules out of the unit-testable service layer and leaves domain `ValidationError` unused.
- **Service ↔ SQLAlchemy session coupling.** `housing_unit_service` imports `sqlalchemy.orm.Session` and threads sessions through every call. Routes correctly avoid repositories, but this is looser than AGENTS.md (“services … never SQLAlchemy sessions or queries directly”). Prefer a thin UoW/session port or keep session ownership only at the API edge if tightening boundaries.
- **`os.getenv` outside settings in tests.** `tests/e2e/conftest.py` reads `E2E_BASE_URL` via `os.getenv`. Application modules are clean; fold test overrides into settings or a dedicated test settings helper for consistency.
- **Nearby success contract gap.** Contract coverage exercises nearby 404 (no coords) and 422 (missing radius) but not success shape / `X-Geo-Approximation: bounding-box` header. Add a positive contract (and preferably e2e) case.
- **CORS setting unused.** `CORS_ALLOWED_ORIGINS` is loaded in settings but `CORSMiddleware` is never registered in `app/main.py`, so browser clients relying on that config will fail CORS preflight unexpectedly.

### P2 (nice to have)
- **RBAC roles not implemented.** AGENTS.md describes `viewer` / `editor` / `admin`; runtime is a single write API key. README documents this as intentional challenge scope — track as known debt before production multi-tenant use.
- **No rate limiting, security headers, or write audit trail.** Documented as production-readiness follow-ups; public GETs are unauthenticated and unbounded beyond FastAPI defaults.
- **Magic pagination defaults.** List defaults `limit=100` / `le=1000` (and nearby `limit=10`) are inline rather than named constants/enums in `app/core/constants.py`.
- **Import script layering.** `app/scripts/import_nyc_data.py` calls the repository (and private `SocrataClient._fetch_page` in dry-run) instead of a service façade — acceptable for a CLI ETL, but duplicates the sync path next to `sync_from_source`.
- **Broad `except Exception` in import.** Page failures are logged and counted, then process exits non-zero — good for ops visibility, but typed ingestion errors would make failure modes clearer.
- **Health is liveness-only.** `/health` does not check DB connectivity; fine for Docker liveness, weak as a readiness probe.
- **Alembic unique constraint on existing data.** `20260424_…_add_socrata_row_id` adds `uq_housing_units_socrata_row_id` without a pre-check/data cleanup step. Safe for empty/greenfield DBs; risky if applied against already-imported duplicate `:id` values. Downgrades correctly drop constraint then column.
- **Composite uniqueness + NULLs.** Postgres treats NULLs as distinct in `uq_housing_units_project_building`, so multiple manual rows without source ids are allowed (intentional) but partial-null source ids are also not uniquely constrained — document or tighten with a partial unique index if needed.

## Suggested next actions
1. Harden `_apply_circle_filter` (reject or clamp latitudes where `|cos(lat)|` is near zero); add a unit/contract test for `center_lat=90`.
2. Fix auth header wiring (`Header(alias=…)`) and switch key compare to `secrets.compare_digest`; extend contract tests if custom header support remains.
3. Move refresh/nearby precondition checks into the service layer using typed domain errors; map them in routes only.
4. Add nearby success contract asserting items schema + `X-Geo-Approximation` header; optionally expand e2e beyond the single CRUD lifecycle.
5. Either register `CORSMiddleware` from `settings.cors_allowed_origins` or remove the unused setting to avoid false confidence.
6. Before production: rate limiting on public GETs, security headers, audit logs on writes, and the documented viewer/editor/admin role model (or explicitly scope the single-key model in ops runbooks).
7. Keep migrations linear; for any future unique/index adds on populated tables, add a data validation/backfill step in the same revision and prefer expandable online DDL patterns when downtime matters.
