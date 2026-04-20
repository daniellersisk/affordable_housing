# FastAPI dependency functions shared across route handlers.
# Includes the DB session dependency and the write auth dependency.
# Step 3 will implement get_db(); Step 7 will implement require_write_auth().
from __future__ import annotations

# TODO: Step 3 - implement get_db() -> AsyncGenerator[Session, None]
# TODO: Step 7 - implement require_write_auth(api_key: str = Header(...)) -> None
#   raise 401 with ErrorCode.UNAUTHORIZED if key is missing or does not match settings
