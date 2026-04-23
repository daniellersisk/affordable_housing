#!/bin/bash
set -e

# migrations run in the dedicated migrate service before this container starts.
# entrypoint.sh is now responsible for the app only.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
