# Reviewer Notes — Housing Units API

## Quickstart

```bash
git clone https://github.com/daniellersisk/affordable_housing
cd affordable_housing

make up
# docs: http://localhost:8000/docs
```

## Load real NYC Open Data (optional)

Set `SODA_APP_TOKEN` in `.env` (recommended), then:

```bash
make import
```

To preview without writing to Postgres:

```bash
make import ARGS=--dry-run
```

## Tests

```bash
make test
make lint
```

## Review scope note (tests/contracts are required)

Per the repo standards, reviewers should treat **test and contract completeness as in-scope and required**:

- **Endpoint tests**: each endpoint should have coverage for success, validation failure, not-found/conflict (as applicable), and auth failure (where applicable).
- **Contract tests**: should verify status codes, response schema shape, and error schema shape (including consistent `{ code, message, details }` error payloads).

## Auth

Write routes require `X-API-Key` (configured via `WRITE_API_KEY` in `.env`).

Note: `.env.example` includes a local-dev `WRITE_API_KEY`. In production, set a strong random key via your secret
manager.

## Intentional trade-offs

- **Import is upsert-only:** it updates/inserts records by `(project_id, building_id)` but does not delete records removed upstream.
- **Geo circle approximation:** nearby/circle filtering uses a bounding-box approximation; responses include `X-Geo-Approximation: bounding-box`.

