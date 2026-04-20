# Housing Units API

Containerized Housing Units API for New York City data built with Python, FastAPI, PostgreSQL, and Docker.

This README is the single source of truth for both implementation guidance and technical design.

## TL;DR for Reviewers

- This project implements a containerized Housing Units API using FastAPI + PostgreSQL.
- Core goals are reproducibility, clear API contracts, durable persistence, and testability.
- Required CRUD + filtering endpoints are defined, along with data ingestion and validation strategy.
- Architecture separates framework code from business logic to avoid endpoint coupling.
- This document includes setup steps, technical design decisions, and production-readiness considerations.

## Quickstart (3 Commands)

```bash
docker compose up --build
docker compose run --rm api alembic upgrade head
docker compose run --rm api python -m app.scripts.import_nyc_data
```

Then open:

- Swagger docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

## Where to Review Key Decisions

- **Architecture boundaries:** `Architecture`
- **API behavior and validation:** `API Contract`
- **Persistence and migrations:** `Data Model (Initial)` + `Docker + Environment Design`
- **Execution sequence:** `Delivery Plan (Order of Work)`
- **Submission quality gates:** `Guardrails from Prior Feedback` + `Definition of Done`

## Tech Stack

- Python 3.12
- FastAPI
- PostgreSQL
- SQLAlchemy + Alembic
- Docker + Docker Compose
- Pytest

### Why Python 3.12

- Strong compatibility across FastAPI, SQLAlchemy, Alembic, and common tooling used in this project.
- Modern typing and runtime improvements help code quality and maintainability without introducing bleeding-edge risk.
- Current and broadly adopted version for backend services, balancing stability with up-to-date language features.
- Practical for interview/reviewer environments where reproducibility and predictable dependency behavior matter.

## Challenge Requirements Covered

### Required Endpoints

- `GET /housing-units`
  - query params: `street_name`, `borough`, `postcode`, `construction_type`, `num_units_min`, `num_units_max`
  - geo filter (Option 1): single-endpoint discriminator using `geo_shape` (`rectangle` or `circle`)
- `GET /housing-units/{id}`
- `POST /housing-units`
- `PUT /housing-units/{id}`
- `DELETE /housing-units/{id}`

### Required Capabilities

- Data loaded from NYC open data source
- Request validation
- Persistent PostgreSQL storage
- Containerized app + dependencies
- Unit, integration, and end-to-end tests

## Data Source Decision (NYC Open Data)

- Use the Socrata dataset API for `hg8x-zxpr`; endpoint path style may vary by API version/docs.
- Configure `SODA_APP_TOKEN` and send it for ingestion requests (required in non-dev environments).
- Pagination is mandatory for imports; never rely on single-page/default limits.
- For ingestion queries, use HTTP `POST` to Socrata `query.json` endpoints (not `GET`) to support full query options and long query payloads.
- Normalize source fields at write-time before persistence.
- Map source `total_units` to API/storage `num_units`.
- Isolate ingestion behind a single shared client module so endpoint/version changes do not affect service/business logic.

Recommended ingestion settings:

- `NYC_OPEN_DATA_URL` (or `NYC_OPEN_DATA_BASE_URL` + `NYC_OPEN_DATA_VIEW_ID`)
- `SODA_APP_TOKEN`
- `INGEST_PAGE_SIZE`
- `INGEST_TIMEOUT_SECONDS`
- `INGEST_MAX_RETRIES`

## Architecture

### Layers

- **API layer:** FastAPI route handlers + schema validation
- **Service layer:** business rules and filtering logic
- **Repository layer:** SQLAlchemy query/data access
- **Persistence layer:** PostgreSQL schema managed with Alembic
- **Ingestion layer:** repeatable data import/upsert command

### Design Principles

- Keep framework code and business logic separate
- Do not duplicate clients or business logic; centralize shared code in top-level modules
- Keep endpoint behavior independent (no hidden endpoint coupling)
- Prefer explicit commands for migrations/import over implicit startup side effects
- Keep docs and runtime behavior aligned

## Project Structure

```text
app/
  main.py
  api/
    routes/
      housing_units.py
  schemas/
  models/
  services/
  repositories/
  db/
    session.py
  scripts/
    import_nyc_data.py
alembic/
tests/
  unit/
  integration/
  e2e/
docker-compose.yml
Dockerfile
requirements.txt
requirements-dev.txt
.env.example
README.md
```

## API Contract

## `GET /housing-units`

Filters are optional and composable:

- `street_name` (string)
- `borough` (string)
- `postcode` (string)
- `construction_type` (string)
- `num_units_min` (int)
- `num_units_max` (int)
- `geo_shape` (`rectangle` or `circle`)

When `geo_shape=rectangle`, required params are:

- `min_lat`, `max_lat`, `min_lon`, `max_lon`

When `geo_shape=circle`, required params are:

- `center_lat`, `center_lon`, `radius_m`

Recommended additional query controls:

- `limit` (default + max bound)
- `offset`

Behavior notes:

- Case-insensitive matching where appropriate
- `num_units_min <= num_units_max` enforced
- Predictable sorting + pagination
- Normalization happens at write-time (for example, borough casing and postcode string handling)
- Reject mixed shape parameters (rectangle params with circle params in the same request)
- Reject missing required geo params for selected `geo_shape`
- Reject geo params provided without `geo_shape` and return `422` with code `INVALID_GEO_FILTER`
- Invalid geo-shape combinations return `422` using `{ code, message, details }`

## `GET /housing-units/{id}`

- Returns single record
- `404` if not found

## `POST /housing-units`

- Validates request body
- Returns `201` with created resource

## `PUT /housing-units/{id}`

- Full update semantics
- `404` if id does not exist
- For source-managed rows (rows with `project_id` and `building_id`), updates are rejected to avoid conflicts with import refresh behavior (`409` recommended).

## `DELETE /housing-units/{id}`

- Deletes record
- Returns `204`
- For source-managed rows (rows with `project_id` and `building_id`), deletes are rejected to prevent confusing reappearance on the next import (`409` recommended).

## Data Model (Initial)

`housing_units`:

- `id` (internal UUID or BIGSERIAL primary key used by API paths)
- `project_id` (source identifier)
- `building_id` (source identifier)
- `street_name` (indexed)
- `borough` (indexed)
- `postcode` (indexed)
- `construction_type` (indexed)
- `num_units` (int, non-negative; mapped from source `total_units`)
- optional location fields (`latitude`, `longitude`)
- `created_at`, `updated_at`

Index strategy:

- Single-column indexes for core filters
- Add composite indexes after measuring query patterns
- Enforce composite uniqueness on source identity (`project_id`, `building_id`) for idempotent imports/upserts

## Public vs Private Endpoints

- **Public:** `GET /housing-units`, `GET /housing-units/{id}`
- **Private (protected):** `POST`, `PUT`, `DELETE`

Suggested roles:

- `viewer` (read-only)
- `editor` (create/update)
- `admin` (create/update/delete)

MVP auth option:

- API key required for write operations (`POST`, `PUT`, `DELETE`)
- Header contract: `X-API-Key`
- Missing/invalid key returns `401` with error payload `{ "code": "...", "message": "...", "details": ... }`
- Source-managed row write contract: `PUT`/`DELETE` return `409` with clear error payload when the target row is source-managed.

Production auth option:

- JWT/OAuth2 with role claims

## Docker + Environment Design

## Services

- `api` container for FastAPI app
- `db` container for PostgreSQL

## Persistence Requirement

Database must live outside container lifecycle:

- Preferred: named Docker volume (`pg_data`)
- Optional: bind mount for local visibility

## Environment Variables

Use:

- `.env.example` committed
- `.env` local only (gitignored)

Suggested vars:

- `APP_ENV`
- `APP_HOST=0.0.0.0`
- `APP_PORT=8000`
- `DATABASE_URL`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `NYC_OPEN_DATA_URL` (or `NYC_OPEN_DATA_BASE_URL` + `NYC_OPEN_DATA_VIEW_ID`)
- `NYC_OPEN_DATA_BASE_URL`
- `NYC_OPEN_DATA_VIEW_ID`
- `SODA_APP_TOKEN`
- `INGEST_PAGE_SIZE`
- `INGEST_TIMEOUT_SECONDS`
- `INGEST_MAX_RETRIES`
- `API_AUTH_ENABLED`
- `WRITE_API_KEY` (required for write protection)
- `WRITE_API_KEY_HEADER` (default `X-API-Key`)
- `CORS_ALLOWED_ORIGINS`

## Local Runbook

## 1) Start stack

```bash
docker compose up --build
```

## 2) Run migrations

```bash
docker compose run --rm api alembic upgrade head
```

## 3) Import NYC data

```bash
docker compose run --rm api python -m app.scripts.import_nyc_data
```

## 4) Verify API

- Swagger docs: `http://localhost:8000/docs`
- OpenAPI spec: `http://localhost:8000/openapi.json`
- Health check: `http://localhost:8000/health`

## 5) Tear down

```bash
docker compose down
```

## 6) Tear down with volume reset (destructive)

```bash
docker compose down -v
```

## Testing Strategy

## Unit tests

- Service logic
- Validation/normalization
- Filter composition
- Tests for every new or changed function

## Integration tests

- API + real Postgres
- Migration-applied schema
- CRUD + filter behavior
- Endpoint-level error mapping and logging behavior checks
- Contract tests for request/response status and schema compatibility

## E2E/system tests

- Full containerized flow:
  - migrate
  - import
  - query/mutate

## Test commands

Run checks through Docker so the repo image is the source of truth:

```bash
docker compose run --rm --no-deps api ruff check .
docker compose run --rm api pytest -q
docker compose run --rm api pytest tests/unit -q
docker compose run --rm api pytest tests/integration -q
docker compose run --rm api pytest tests/e2e -q
docker compose run --rm api pytest tests/contract -q
```

Contract test conventions and starter layout live in `tests/contract/README.md`.

## Linting and CI

- The `api` image installs both runtime and dev requirements so linting and tests can run inside Docker.
- `ruff` configuration lives in `pyproject.toml`.
- CI runs the baseline checks from `.github/workflows/ci.yml`.

## Security and API Concerns

- Validate all inputs
- Enforce pagination limits
- Add rate limiting for public APIs
- Restrict CORS by environment
- Keep secrets out of repo
- Use least-privileged DB credentials
- Prefer non-root container user
- Keep dependencies and base images updated
- Keep clear role boundaries even for public APIs (public reads, protected writes)
- Ensure each endpoint has explicit error handling and structured logs
- Add security headers/CSP strategy for production deployments
- Add audit logging for write operations (who did what and when)
- Define secret rotation/source-of-truth approach (vault/secret manager)
- Include supply-chain checks (dependency CVEs plus lockfile/integrity practices)
- Include CSRF protections if cookie-based auth is used

## Production Readiness Checklist

- Health and readiness probes
- Structured logs
- CI for lint, tests, build
- Migration step in deployment pipeline
- Dependency and image vulnerability scanning
- Backup/restore strategy for Postgres
- Environment-specific config and secret management

## Delivery Plan (Order of Work)

1. Project skeleton and tooling baseline
2. Dockerized app + DB environment
3. PostgreSQL models and Alembic migrations
4. Service/repository layer implementation
5. Required CRUD + filtering endpoints
6. NYC data import and idempotent upsert
7. Public/private endpoint authorization
8. Unit/integration/e2e testing
9. Production-hardening pass

## Guardrails from Prior Feedback

Use this as a hard pre-submit checklist:

- All runtime dependencies are explicitly declared
- API binds correctly to `0.0.0.0` and works on localhost
- Every endpoint is manually exercised before submission
- No unintended coupling of POST to GET preconditions
- Business logic is separated from framework handlers
- Source-managed records are read-only for `PUT`/`DELETE` to keep import refresh semantics predictable and reviewer-friendly
- Migration requirements for tests are documented
- Tests are performant and layered
- Contract tests are present and updated for any endpoint contract change
- Type hints are present on core/public functions
- Avoid committing large generated/static artifacts when better storage options exist

## Definition of Done

This project is ready to hand off when:

- Required endpoints work as specified
- Swagger docs accurately reflect implementation
- Docker setup works from a clean clone
- Data persists across container restarts
- Migrations and import are repeatable
- Public/private behavior is enforced
- Tests run from documented commands
- Another engineer can run and evaluate without hidden setup knowledge
