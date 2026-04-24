# QA / Pre-Review Scope (shareable)

This document is intended to make review efficient by clarifying:

- what is **in scope** for this preliminary review
- what is **implemented** vs **intentionally deferred**
- known gaps that are **required** but not finished yet

## Review focus (please review now)

- **Architecture boundaries**
  - Route handlers call services only
  - Services call repositories only
  - Repositories are the only layer that touches SQLAlchemy sessions/queries
  - Services raise typed domain errors; API layer maps them to HTTP responses

- **NYC Open Data ingestion / refresh behavior**
  - Idempotent import behavior (stable Socrata `:id`–based identity)
  - Clear refresh behavior and error contracts
  - Centralized Socrata client usage and pagination expectations

- **API contracts + error mapping consistency**
  - Response schemas for read endpoints
  - Structured error payload shape: `{ code, message, details }`
  - Correct status codes for validation/not-found/conflict/auth

- **Geo filtering (current behavior)**
  - `geo_shape` discriminator behavior (rectangle vs circle)
  - Circle approximation behavior, including `X-Geo-Approximation` response header

- **Docs/runbook alignment**
  - `README.md` reflects what is implemented and how to run/test it
  - Reviewer notes reflect intentional trade-offs and current behavior

- **Test/contract completeness (required)**
  - Per-endpoint coverage: success, validation failure, not-found/conflict, auth failure (where applicable)
  - Contract coverage: status codes, response schemas, and consistent error schema `{ code, message, details }`

## Implemented (current baseline)

- Dockerized FastAPI + Postgres stack; migrations apply on startup (idempotent)
- Repository/service layering with typed domain errors and explicit error mapping in routes
- CRUD + filtering endpoints per README baseline
- Import + refresh workflow against Socrata, including upsert/idempotency improvements
- CI: lint + migrations gates + tests
- Documentation updates for reviewers and runbook clarity
- Automation: scheduled repo-health report PR generation

## Intentionally deferred (safe to defer for *this* pre-review)

- **RBAC / least-privilege roles**
  - Current write access is a single `X-API-Key` gate (no viewer/editor/admin model yet)
  - Future work: role-bearing auth, per-route authorization, and `403` contract

- **Production-grade geo (PostGIS)**
  - Circle filtering is currently a bounding-box approximation
  - Future work: PostGIS (e.g., `ST_DWithin`) + spatial index and exact distance semantics

## Required but in-progress (please review gaps; do not assume complete yet)

- **Endpoint tests (coverage expansion)**
  - Goal: every route has tests for success, validation failure, not-found/conflict, and auth failure (where applicable)

- **Contract tests (error schema consistency)**
  - Goal: consistent `{ code, message, details }` assertions across all endpoints for 4xx/5xx responses

- **Production hardening**
  - Rate limiting / throttling strategy (`429` contract)
  - Security headers (and explicit CSP decision if needed)
  - Audit logging for write operations
  - Deployment runbook + operational checks (readiness, metrics, alerting expectations)

## How to test (reviewers)

```bash
make up
make lint
make test
```

Optional (requires `SODA_APP_TOKEN` for best results outside local dev):

```bash
make import
```

