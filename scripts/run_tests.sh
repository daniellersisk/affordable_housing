#!/usr/bin/env bash
set -euo pipefail

# Deterministic test runner:
# - ensures db is up
# - creates an ephemeral test database inside the same Postgres container
# - runs migrations + pytest against that DB (via DATABASE_URL override)
# - drops the test DB at the end

PROJECT_DB_NAME="${POSTGRES_DB:-affordable_housing}"
TEST_DB_NAME="${TEST_DB_NAME:-${PROJECT_DB_NAME}_test}"

POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"

# Reconstruct a DATABASE_URL that points at the test database.
# Note: we intentionally use the docker-compose network hostname `db`.
TEST_DATABASE_URL="${TEST_DATABASE_URL:-postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${TEST_DB_NAME}}"

echo "Starting db (if needed)…"
docker compose up -d db >/dev/null

echo "Waiting for db health…"
for i in $(seq 1 30); do
  if docker compose exec -T db pg_isready -U "${POSTGRES_USER}" -d "${PROJECT_DB_NAME}" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "Creating clean test database '${TEST_DB_NAME}'…"
docker compose exec -T db psql -U "${POSTGRES_USER}" -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS \"${TEST_DB_NAME}\";"
docker compose exec -T db psql -U "${POSTGRES_USER}" -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE \"${TEST_DB_NAME}\";"

cleanup() {
  echo "Dropping test database '${TEST_DB_NAME}'…"
  docker compose exec -T db psql -U "${POSTGRES_USER}" -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS \"${TEST_DB_NAME}\";" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Running migrations + pytest against test DB…"
docker compose run --rm --no-deps \
  -e APP_ENV=test \
  -e DATABASE_URL="${TEST_DATABASE_URL}" \
  api alembic upgrade head

docker compose run --rm --no-deps \
  -e APP_ENV=test \
  -e DATABASE_URL="${TEST_DATABASE_URL}" \
  api pytest -q

