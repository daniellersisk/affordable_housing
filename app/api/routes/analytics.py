from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.logging import get_logger
from app.repositories import analytics_repository as repo

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/analytics", tags=["analytics — public"])


class BoroughSummaryResponse(BaseModel):
    borough: str | None
    total_units: int
    record_count: int


class ConstructionTypeSummaryResponse(BaseModel):
    construction_type: str | None
    record_count: int


class AnalyticsSummaryResponse(BaseModel):
    total_units: int
    total_records: int
    units_by_borough: list[BoroughSummaryResponse]
    top_construction_types: list[ConstructionTypeSummaryResponse]


@router.get("/summary", response_model=AnalyticsSummaryResponse)
def get_summary(session: Session = Depends(get_db)) -> AnalyticsSummaryResponse:
    """Dashboard summary: total units, total records, units by borough, top construction types."""
    logger.info("GET /v1/analytics/summary")
    summary = repo.get_summary(session)
    return AnalyticsSummaryResponse(
        total_units=summary.total_units,
        total_records=summary.total_records,
        units_by_borough=[
            BoroughSummaryResponse(
                borough=b.borough,
                total_units=b.total_units,
                record_count=b.record_count,
            )
            for b in summary.units_by_borough
        ],
        top_construction_types=[
            ConstructionTypeSummaryResponse(
                construction_type=t.construction_type,
                record_count=t.record_count,
            )
            for t in summary.top_construction_types
        ],
    )
