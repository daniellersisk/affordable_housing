# BugBot Review Rules — Housing Units API

## Architecture

- Route handlers must only call services — never repositories or SQLAlchemy directly.
- Services must only call repositories — never SQLAlchemy sessions or queries directly.
- Never import FastAPI, HTTPException, or Request in the service layer.
- Services raise typed domain errors (NotFoundError, ConflictError, ValidationError from app/core/errors.py).
- Route handlers own all error mapping — catch domain errors and return structured HTTP responses.

## Error responses

- All 4xx/5xx responses must use the shape `{ code, message, details }`.
- Never branch on raw exception message strings — use typed exceptions or error codes.
- Error codes must come from the ErrorCode enum in app/core/constants.py.

## Config and secrets

- Only app/settings.py may call os.getenv(). All other modules must import from settings.
- No hardcoded secrets, tokens, or credentials anywhere in code or comments.
- Logs must never contain secret values (API keys, tokens, passwords).

## Testing

- Every new or changed function must have a test.
- Every new or changed endpoint must have tests for: success, validation failure, not-found/conflict, and auth failure.
- Contract tests must verify status codes, response schema shape, and error schema shape.

## Ingestion

- All Socrata API access must go through app/clients/socrata_client.py — no direct HTTP calls to Socrata elsewhere.
- Source field normalization (total_units → num_units, etc.) must happen in the repository layer only.
