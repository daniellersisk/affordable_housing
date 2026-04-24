# AGENTS Guide - Housing Units API

Read this before writing code. These rules are mandatory for any agent working in this repo.

## Mission

Build and maintain a containerized Housing Units API with:

- Python 3.12
- FastAPI
- PostgreSQL
- Docker + Docker Compose

Python 3.12 is the project baseline because it provides a stable, well-supported target for the FastAPI/PostgreSQL stack while keeping modern typing/performance improvements and minimizing environment drift for reviewers.

## Source of Truth

- Primary design and runbook: `README.md`
- Agent operating standards: `AGENTS.md`
- Keep docs and implementation in sync in the same change set.

## Non-Negotiable Engineering Rules

- **No duplicate clients or duplicate business logic.** Shared clients/utilities live once in top-level app modules and are reused.
- **Imports at top of file only.** No inline imports, except `TYPE_CHECKING` guard cases.
- **Config via settings object only.** Only `app/settings.py` may read environment variables (`os.getenv()`); all other modules must import from `settings`.
- **No magic strings/numbers.** Use constants/enums for repeated values and domain states.
- **Type hints required.** Add explicit type hints for public functions and service interfaces.
- **No large generated/static artifacts** when in-memory or DB-backed approaches are better.

## Architecture and Boundaries

- Keep route handlers thin and declarative.
- Put domain/business logic in service modules.
- Put SQLAlchemy queries/data access in repository modules.
- Do not couple write endpoints to prerequisite read endpoint calls.
- Use explicit commands for migrations/imports; avoid hidden side effects on app startup.

### Layer Separation Rules (non-negotiable)

The call chain is always: `route handler → service → repository → database`. Never skip or reverse a layer.

- **Route handlers** call services only — never repositories directly.
- **Services** call repositories only — never SQLAlchemy sessions or queries directly.
- **Repositories** are the only layer that may import or use SQLAlchemy sessions, queries, or the ORM.
- **Never import FastAPI, `HTTPException`, or `Request` in the service layer.** Services are pure Python business logic and must be testable without an HTTP server or FastAPI context.
- **Services raise typed domain errors** (`NotFoundError`, `ConflictError`, `ValidationError` from `app/core/errors.py`). They never raise `HTTPException`.
- **Route handlers own error mapping** — they catch domain errors and translate them to the correct HTTP status codes and structured error payloads. This mapping lives in one place only.

```
HTTP request
    → route handler  (FastAPI — parse input, map errors, return output)
        → service    (pure Python — business rules, typed errors)
            → repository  (SQLAlchemy — sessions, queries, persistence)
                → database
```

## NYC Open Data Ingestion Standard

- Use Socrata dataset API access for `hg8x-zxpr`; do not hardcode one endpoint style in business code.
- Configure and send `SODA_APP_TOKEN` for ingestion (required outside local development).
- Pagination is mandatory for imports (`get_all()` or explicit page/offset loop).
- Use HTTP `POST` for Socrata ingestion queries (`query.json`) instead of `GET`.
- Keep external data access in one shared ingestion client (no duplicated API clients).
- Keep ingestion retry/pagination/timeout values in config (`INGEST_PAGE_SIZE`, `INGEST_TIMEOUT_SECONDS`, `INGEST_MAX_RETRIES`).
- Normalize source fields at write-time before persistence.
- Map source `total_units` to internal/API `num_units`.
- Use internal DB `id` as API identity; keep source identity in (`project_id`, `building_id`) with composite uniqueness.
- Treat source-managed rows (with source identity present) as read-only for `PUT`/`DELETE`; return `409` with a clear message.
- Rationale: imported records are synchronized from the upstream source, so blocking edits/deletes avoids surprising overwrite/resurrection behavior during refresh.

## Logging and Error Handling Standards

- Every endpoint must have clear error handling and structured logging.
- Log request start, success, and failure paths with useful context (operation, id/filter scope, status).
- Use layered error handling:
  - repository/client errors -> service/domain errors
  - service/domain errors -> mapped HTTP responses in API layer
- Never branch on raw error message strings; use typed exceptions/error codes.
- Do not use `print()` for runtime observability.

## Testing Standards

- Add tests for every function created or changed.
- Contract tests are mandatory for API behavior and must be updated whenever endpoint contracts change.
- Each endpoint requires tests for:
  - success path
  - validation failure path
  - not-found or conflict path (as relevant)
  - auth/permission failure (for protected routes)
- Contract tests must verify:
  - response status codes
  - response schema/shape
  - required/optional field semantics
  - error response schema for 4xx/5xx paths
- For geo filtering, tests must verify `geo_shape` discriminator behavior:
  - rectangle required params (`min_lat`, `max_lat`, `min_lon`, `max_lon`)
  - circle required params (`center_lat`, `center_lon`, `radius_m`)
  - mixed/missing params return `422` with `{ code, message, details }`
  - geo params without `geo_shape` return `422` with `code=INVALID_GEO_FILTER`
- System/e2e tests must call the API over HTTP, not instantiate services directly.
- Keep tests deterministic and reasonably fast; document any migration/setup requirements.

## Roles and Security (Public API Included)

Even if read endpoints are public, roles and security are still required:

- Public: `GET /v1/housing-units`, `GET /v1/housing-units/{id}`
- Protected: `POST`, `PUT`, `DELETE`
- Write-route auth contract:
  - header: `X-API-Key`
  - missing/invalid key: `401` with `{ code, message, details }`
- Source-managed row contract:
  - `PUT`/`DELETE` on source-managed rows return `409` with `{ code, message, details }`
- Minimum role model:
  - `viewer` -> read-only
  - `editor` -> create/update
  - `admin` -> create/update/delete
- Apply least privilege, input validation, and rate limiting strategy.

## Multi-Agent Workflow (Guide from Screenshot)

Use these responsibilities when splitting work:

- **Architect:** produces or updates technical spec/design only.
- **Builder:** implements strictly to spec and does not bypass guardrails.
- **QA:** validates behavior against spec and tests gaps/regressions using `agents/qa.mdc`.
- **Security:** audits auth, validation, secrets handling, and API abuse risks using `agents/security.mdc`.

Architect/QA/Security should not silently rewrite implementation scope; Builder should not freestyle beyond accepted design without updating spec first.

## Security Agent Requirements

When security review is requested, use `agents/security.mdc` and validate:

- OWASP-focused categories (injection, auth/session, sensitive data, deserialization, access control, misconfiguration, XSS risk, dependencies)
- Cross-cutting checks (hardcoded secrets, input validation, sensitive logging, safe error mapping)
- Additional controls that are commonly missed:
  - rate limiting/throttling
  - CSRF (if cookie-based auth is used)
  - security headers/CSP
  - audit logging for write operations
  - secret rotation and secret-manager sourcing
  - supply-chain integrity beyond CVE scans

## QA Agent Requirements

When QA review is requested, use `agents/qa.mdc` and validate:

- Unit test coverage for every new/changed function
- Endpoint test coverage for success/failure/auth paths
- Mandatory contract tests for endpoint behavior and schemas
- Integration/e2e behavior via HTTP with documented setup
- Regression checks for endpoint coupling, role boundaries, and docs parity

## Build Order (Default)

1. Project skeleton and tooling baseline
2. Dockerized app + database
3. PostgreSQL models and Alembic migrations
4. Service/repository implementation
5. CRUD + filtering endpoints
6. NYC data import with idempotent upsert
7. Public/private authorization boundaries
8. Unit/integration/e2e testing
9. Production-readiness hardening

## Required API Endpoints

- `GET /v1/housing-units` with filters:
  - `street_name`, `borough`, `postcode`, `construction_type`, `num_units_min`, `num_units_max`
  - geo discriminator `geo_shape`:
    - `rectangle` -> `min_lat`, `max_lat`, `min_lon`, `max_lon`
    - `circle` -> `center_lat`, `center_lon`, `radius_m`
- `GET /v1/housing-units/{id}`
- `POST /v1/housing-units`
- `PUT /v1/housing-units/{id}`
- `DELETE /v1/housing-units/{id}`
- `POST /v1/housing-units/{id}/refresh` — re-sync one existing record from Socrata using its `project_id` + `building_id`. No request body. Returns `404` if the unit does not exist, `422` if the unit has no source identity.
- `POST /v1/housing-units/sync` — fetch and upsert a specific Socrata record by source identity. Body: `{ project_id, building_id }`. Inserts if not yet in DB, updates if already present. Use this to add or re-sync a single record without running a full import.

### Mutation operations — full reference

| Operation | Endpoint | Socrata? | Payload | Use case |
|---|---|---|---|---|
| user edit | `PUT /v1/housing-units/{id}` | no | user data | update any field manually |
| re-sync one known record | `POST /v1/housing-units/{id}/refresh` | yes | none | refresh a record already in the DB |
| add/sync by source identity | `POST /v1/housing-units/sync` | yes | `{ project_id, building_id }` | sync one specific Socrata record without a full import |
| bulk re-sync | `make refresh` / `make import` | yes | none | re-import everything from Socrata |

Both `/refresh` and `/sync` depend on the Socrata client (Phase 4) and land in the same change set.

## Definition of Done

Do not mark complete until all are true:

- Required endpoints are implemented and manually verified.
- Endpoint logs + error mappings are present and understandable.
- Tests exist for every new/changed function and endpoint paths.
- Contract tests pass for all public and protected endpoint contracts.
- Docker startup works from clean clone.
- Postgres persistence survives container restarts.
- Migrations/import process is repeatable and documented.
- Public/private role behavior is enforced and tested.

