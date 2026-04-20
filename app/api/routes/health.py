# Health check route.
# Returns a simple liveness response used by Docker healthchecks and monitoring.
# Does not require auth or a database connection.
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    """Liveness check endpoint."""
    return {"status": "ok"}
