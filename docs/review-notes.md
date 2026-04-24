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

## Auth

Write routes require `X-API-Key` (configured via `WRITE_API_KEY` in `.env`).

## Intentional trade-offs

- **Import is upsert-only:** it updates/inserts records by `(project_id, building_id)` but does not delete records removed upstream.
- **Geo circle approximation:** nearby/circle filtering uses a bounding-box approximation; responses include `X-Geo-Approximation: bounding-box`.

