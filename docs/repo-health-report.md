# Repo Health Report

Date: 2026-04-25

## Summary

- **CI:** `make lint` and `make test` both exited **0** per supplied logs (Ruff clean; pytest quiet run after image pull).
- **Layering:** Core housing-unit flows follow **route → service → repository**; **`GET /v1/analytics/summary` bypasses the service layer** and calls `analytics_repository` directly from the route module.
- **Standards vs code:** Workspace/AGENTS rules require **409 on `PUT`/`DELETE` for source-managed rows** (`project_id` + `building_id` present). The implementation and unit tests **explicitly allow** updating and deleting those rows — **spec and enforcement are out of sync**.
- **Secrets (static):** No live credentials observed in application code. **`.env` is gitignored** (good). **`.env.example`** uses obvious local placeholders. **`README.md`** shows a `git clone` URL with a **`<TOKEN>` placeholder** — fine as documentation if never replaced with a real token and committed.
- **Migrations:** Alembic history is linear and additive; **downgrades drop constraints/columns in safe order** for the `socrata_row_id` revision. No data backfills or destructive upgrades in reviewed revisions.
- **Tests / API semantics:** Contract tests assert presence of list `total` but **not** that it equals a global match count; the list handler sets **`total` to the length of the current page result**, which can mislead clients expecting a full-result count.

## Checks Run

- `make lint` (exit=0) — Ruff: “All checks passed!”
- `make test` (exit=0) — `docker compose run --rm api pytest -q` (output began with image pull layers)

## Findings (prioritized)

### P0 (must fix)

- **Source-managed mutation policy:** `AGENTS.md` and `.cursor/rules/housing-api-agent-standards.mdc` require treating rows with source identity as **read-only for `PUT`/`DELETE`** with **409** and structured error body. **`app/services/housing_unit_service.py` documents the opposite choice**, and **`app/repositories/housing_unit_repository.py` `update`/`delete` do not enforce a source-managed guard**. Unit tests (`test_update_housing_unit_allows_source_managed_rows`, `test_delete_housing_unit_allows_source_managed_rows`) lock in the non-compliant behavior. This needs a **single agreed rule** (update docs *or* implement 409 + tests).

### P1 (should fix)

- **Route → repository skip:** `app/api/routes/analytics.py` imports **`analytics_repository` directly**. Per project rules, a thin **`analytics` service** should sit between the route and repository so boundaries stay consistent with the rest of the API.
- **List response `total` semantics:** `list_housing_units` returns `total=len(units)` (page row count after limit), not a **total matching the filter set**. If the API contract is meant to support pagination UX, consider **`total` = full count** (extra query) or rename/clarify the field; **contract tests do not catch** the ambiguity.
- **Error-code mapping coupled to message text:** `app/api/routes/housing_units.py` maps geo validation to `INVALID_GEO_FILTER` by checking whether **`"INVALID_GEO_FILTER" in msg`**, where `msg` comes from Pydantic `ValueError` strings in `app/schemas/filters.py`. This works today but **violates the spirit of “don’t branch on raw message text”**; a typed/custom error or structured validation context would be more robust.

### P2 (nice to have)

- **`analytics_repository`:** No dedicated **unit tests** under `tests/unit/` (coverage relies on e2e/contract paths).
- **Operational hardening:** `GET /v1/analytics/summary` performs **full-table aggregates**; the docstring already notes caching at scale — **rate limiting / caching** remain future production items per security/ops guidance in `AGENTS.md`.
- **`app/scripts/import_nyc_data.py`:** Uses **`print`** for human-readable status; project logging standards prefer structured logging for runtime observability (minor for a CLI script).
- **Repository raising domain errors:** `housing_unit_repository` raises **`NotFoundError` / `ConflictError`** in some paths. Acceptable if team-standard, but some codebases keep **all domain errors in the service layer** for a sharper repository boundary.

## Suggested next actions

1. **Decide and document** whether source-managed rows are immutable for API writes; if yes, implement **409 + contract tests** and remove conflicting service comments/tests; if no, **update `AGENTS.md` and workspace rules** so agents and reviewers are not misled.
2. Introduce **`app/services/analytics_service.py`** (or equivalent) and change **`analytics` routes** to depend on it only.
3. Clarify **`HousingUnitListResponse.total`** (behavior + OpenAPI description) and extend **contract tests** to lock the intended semantics.
4. Replace **string sniffing** for `INVALID_GEO_FILTER` with a **structured validation signal** (e.g. custom exception type or Pydantic error `type`/context) aligned with project error-handling standards.
5. Add **unit tests** for `analytics_repository.get_summary` (happy path + error propagation) if analytics remain part of the supported surface.
