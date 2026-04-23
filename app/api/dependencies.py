from __future__ import annotations

from fastapi import Depends, Header, HTTPException

from app.core.constants import ErrorCode
from app.db.session import get_db
from app.settings import settings

# re-export get_db so route handlers import from one place
__all__ = ["get_db", "require_write_auth"]


def require_write_auth(x_api_key: str = Header(default="")) -> None:
    """Dependency for protected write routes (POST, PUT, DELETE).

    Validates the X-API-Key header against settings.write_api_key.
    Returns None on success; raises 401 with structured error on failure.
    Auth can be disabled entirely via API_AUTH_ENABLED=false for local dev.
    """
    if not settings.api_auth_enabled:
        return
    if not x_api_key or x_api_key != settings.write_api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "code": ErrorCode.UNAUTHORIZED,
                "message": "missing or invalid api key",
                "details": [{"field": "X-API-Key", "message": "header is missing or incorrect"}],
            },
        )


# convenience alias so routes can: from app.api.dependencies import SessionDep
SessionDep = Depends(get_db)
