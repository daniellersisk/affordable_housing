from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.housing_unit import HousingUnit

logger = get_logger(__name__)


@dataclass
class BoroughSummary:
    borough: str | None
    total_units: int
    record_count: int


@dataclass
class ConstructionTypeSummary:
    construction_type: str | None
    record_count: int


@dataclass
class AnalyticsSummary:
    total_units: int
    total_records: int
    units_by_borough: list[BoroughSummary]
    top_construction_types: list[ConstructionTypeSummary]


def get_summary(session: Session, top_construction_types: int = 3) -> AnalyticsSummary:
    """Return aggregate analytics across all housing units."""
    try:
        total_units, total_records = _get_totals(session)
        units_by_borough = _get_units_by_borough(session)
        top_types = _get_top_construction_types(session, top_construction_types)
        logger.info("analytics summary computed", extra={"total_records": total_records})
        return AnalyticsSummary(
            total_units=total_units,
            total_records=total_records,
            units_by_borough=units_by_borough,
            top_construction_types=top_types,
        )
    except SQLAlchemyError as exc:
        logger.error("get_summary failed", extra={"error": str(exc)})
        raise


def _get_totals(session: Session) -> tuple[int, int]:
    stmt = select(
        func.coalesce(func.sum(HousingUnit.num_units), 0),
        func.count(HousingUnit.id),
    )
    row = session.execute(stmt).one()
    return int(row[0]), int(row[1])


def _get_units_by_borough(session: Session) -> list[BoroughSummary]:
    stmt = (
        select(
            HousingUnit.borough,
            func.coalesce(func.sum(HousingUnit.num_units), 0).label("total_units"),
            func.count(HousingUnit.id).label("record_count"),
        )
        .group_by(HousingUnit.borough)
        .order_by(func.sum(HousingUnit.num_units).desc())
    )
    rows = session.execute(stmt).all()
    return [
        BoroughSummary(
            borough=row.borough,
            total_units=int(row.total_units),
            record_count=int(row.record_count),
        )
        for row in rows
    ]


def _get_top_construction_types(session: Session, limit: int) -> list[ConstructionTypeSummary]:
    stmt = (
        select(
            HousingUnit.construction_type,
            func.count(HousingUnit.id).label("record_count"),
        )
        .where(HousingUnit.construction_type.isnot(None))
        .group_by(HousingUnit.construction_type)
        .order_by(func.count(HousingUnit.id).desc())
        .limit(limit)
    )
    rows = session.execute(stmt).all()
    return [
        ConstructionTypeSummary(
            construction_type=row.construction_type,
            record_count=int(row.record_count),
        )
        for row in rows
    ]
