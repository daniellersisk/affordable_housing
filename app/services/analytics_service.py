from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.repositories import analytics_repository as repo

logger = get_logger(__name__)



def get_summary(session: Session, *, top_construction_types: int = 3) -> repo.AnalyticsSummary:
    """Return aggregate analytics across all housing units."""
    logger.info("get_analytics_summary", extra={"top_construction_types": top_construction_types})
    return repo.get_summary(session, top_construction_types=top_construction_types)

