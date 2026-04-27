# Health check route.
# Returns a simple liveness response used by Docker healthchecks and monitoring.
# Does not require auth or a database connection.
from __future__ import annotations

from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Liveness check endpoint."""
    return HealthResponse(status="ok")
