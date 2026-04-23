#!/bin/bash
set -e

echo '{"event": "migration_start", "command": "alembic upgrade head"}'

if alembic upgrade head; then
    echo '{"event": "migration_success", "status": "ok"}'
else
    echo '{"event": "migration_failed", "status": "error"}' >&2
    exit 1
fi
