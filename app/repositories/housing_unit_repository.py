from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import asc, desc, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.constants import (
    SOCRATA_ROW_IDENTITY_CONSTRAINT,
    SOURCE_IDENTITY_CONSTRAINT,
    GeoShape,
    SortOrder,
)
from app.core.errors import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.models.housing_unit import HousingUnit
from app.schemas.filters import HousingUnitFilters

logger = get_logger(__name__)

# flush() sends sql to the db but doesn't commit — changes live in the transaction
# and are visible in the same session. commit() makes them permanent.
# we flush once per logical operation so sqlalchemy batches all dirty fields
# into a single update instead of one round trip per field change.
# the route handler owns commit/rollback; the repo just flushes.

# approximate meters per degree of latitude (constant — latitude lines are parallel)
_METERS_PER_DEGREE_LAT = 111_111.0


def get_by_id(session: Session, unit_id: int) -> HousingUnit | None:
    """Fetch a single housing unit by internal id. Returns None if not found."""
    try:
        return session.get(HousingUnit, unit_id)
    except SQLAlchemyError as exc:
        logger.error("get_by_id failed", extra={"unit_id": unit_id, "error": str(exc)})
        raise


def list_with_filters(session: Session, filters: HousingUnitFilters) -> list[HousingUnit]:
    """Return housing units matching all provided filters with pagination."""
    stmt = select(HousingUnit)

    if filters.street_name:
        stmt = stmt.where(HousingUnit.street_name.ilike(f"%{filters.street_name}%"))
    if filters.borough:
        # exact case-insensitive match — ilike without wildcards
        stmt = stmt.where(HousingUnit.borough.ilike(filters.borough))
    if filters.postcode:
        stmt = stmt.where(HousingUnit.postcode == filters.postcode)
    if filters.construction_type:
        stmt = stmt.where(HousingUnit.construction_type.ilike(f"%{filters.construction_type}%"))
    if filters.num_units_min is not None:
        stmt = stmt.where(HousingUnit.num_units >= filters.num_units_min)
    if filters.num_units_max is not None:
        stmt = stmt.where(HousingUnit.num_units <= filters.num_units_max)

    if filters.geo_shape == GeoShape.RECTANGLE:
        stmt = _apply_rectangle_filter(stmt, filters)
    elif filters.geo_shape == GeoShape.CIRCLE:
        stmt = _apply_circle_filter(stmt, filters)

    sort_col = getattr(HousingUnit, filters.sort_by.value)
    order_fn = asc if filters.sort_order == SortOrder.ASC else desc
    stmt = stmt.order_by(order_fn(sort_col)).limit(filters.limit).offset(filters.offset)

    try:
        results = list(session.execute(stmt).scalars())
        logger.info("list_with_filters", extra={"count": len(results)})
        return results
    except SQLAlchemyError as exc:
        logger.error("list_with_filters failed", extra={"error": str(exc)})
        raise


def create(session: Session, data: dict[str, Any]) -> HousingUnit:
    """Insert a new housing unit. Raises ConflictError on duplicate source identity."""
    unit = HousingUnit(**data)
    session.add(unit)
    try:
        session.flush()
    except IntegrityError as exc:
        raise ConflictError("housing unit with these source ids already exists") from exc
    logger.info("housing unit created", extra={"id": unit.id})
    return unit


def update(session: Session, unit_id: int, data: dict[str, Any]) -> HousingUnit:
    """Update an existing housing unit by id. Raises NotFoundError if not found."""
    unit = session.get(HousingUnit, unit_id)
    if unit is None:
        raise NotFoundError(f"housing unit {unit_id} not found")
    for key, value in data.items():
        setattr(unit, key, value)
    try:
        session.flush()
    except IntegrityError as exc:
        raise ConflictError("update conflicts with an existing record") from exc
    logger.info("housing unit updated", extra={"id": unit_id})
    return unit


def delete(session: Session, unit_id: int) -> None:
    """Delete a housing unit by id. Raises NotFoundError if not found."""
    unit = session.get(HousingUnit, unit_id)
    if unit is None:
        raise NotFoundError(f"housing unit {unit_id} not found")
    session.delete(unit)
    session.flush()
    logger.info("housing unit deleted", extra={"id": unit_id})


def get_by_source_identity(
    session: Session, project_id: str, building_id: str
) -> HousingUnit | None:
    """Fetch a single housing unit by its Socrata source composite identity.

    Returns None if no row with that (project_id, building_id) exists.
    Uses a direct SELECT to bypass the session identity map after a bulk upsert.
    """
    try:
        stmt = select(HousingUnit).where(
            HousingUnit.project_id == project_id,
            HousingUnit.building_id == building_id,
        )
        return session.execute(stmt).scalar_one_or_none()
    except SQLAlchemyError as exc:
        logger.error(
            "get_by_source_identity failed",
            extra={"project_id": project_id, "building_id": building_id, "error": str(exc)},
        )
        raise


def upsert_from_source(session: Session, records: list[dict[str, Any]]) -> int:
    """Idempotent upsert for source-ingested records.

    Normalizes source field names at write time (total_units -> num_units).
    Sets last_synced_from_socrata to the current UTC time on every upsert.
    Uses INSERT ... ON CONFLICT on (project_id, building_id) to update existing rows.
    Returns the number of rows upsert-attempted (only records with a complete
    (project_id, building_id) composite identity are eligible).
    """
    if not records:
        return 0

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Strategy:
    # - If a record has (project_id, building_id), upsert on that composite identity.
    #   This ensures refresh updates the existing row even if socrata_row_id was not yet stored.
    # - Otherwise, upsert on Socrata system row id (":id").
    #
    # Note: socrata_row_id is globally unique. If a record has a composite identity but its
    # socrata_row_id already exists on a *different* composite identity, we route that record
    # to the Socrata upsert path to avoid an IntegrityError on uq_housing_units_socrata_row_id.
    by_source_identity = [r for r in records if _has_complete_source_identity(r)]
    remainder = [r for r in records if not _has_complete_source_identity(r)]
    by_socrata_id = [r for r in remainder if _has_socrata_row_id(r)]

    # Detect socrata_row_id conflicts inside the composite upsert batch.
    composite_with_socrata = [r for r in by_source_identity if _has_socrata_row_id(r)]
    if composite_with_socrata:
        socrata_ids = [
            str(r.get(":id")).strip()
            for r in composite_with_socrata
            if r.get(":id") is not None
        ]
        stmt = select(
            HousingUnit.socrata_row_id,
            HousingUnit.project_id,
            HousingUnit.building_id,
        ).where(HousingUnit.socrata_row_id.in_(socrata_ids))
        existing = session.execute(stmt).all()
        existing_by_socrata: dict[str, tuple[str | None, str | None]] = {
            row[0]: (row[1], row[2]) for row in existing if row[0] is not None
        }

        conflicts: list[dict[str, Any]] = []
        safe: list[dict[str, Any]] = []
        for r in by_source_identity:
            if not _has_socrata_row_id(r):
                safe.append(r)
                continue
            rid = str(r.get(":id")).strip()
            existing_ids = existing_by_socrata.get(rid)
            if existing_ids is None:
                safe.append(r)
                continue
            if existing_ids != (
                str(r.get("project_id")).strip(),
                str(r.get("building_id")).strip(),
            ):
                conflicts.append(r)
            else:
                safe.append(r)

        if conflicts:
            logger.warning(
                "routing composite-identified records to socrata-id upsert due to "
                "socrata_row_id conflicts",
                extra={"conflicts": len(conflicts)},
            )
            by_source_identity = safe
            by_socrata_id.extend(conflicts)

    skipped = len(records) - len(by_source_identity) - len(by_socrata_id)
    if skipped:
        logger.warning(
            "skipping source records missing both composite source ids and socrata :id",
            extra={"skipped": skipped, "received": len(records)},
        )

    total_attempted = 0

    try:
        if by_source_identity:
            normalized = [
                {**_normalize_source_record(r), "last_synced_from_socrata": now}
                for r in by_source_identity
            ]
            stmt = pg_insert(HousingUnit).values(normalized)
            stmt = stmt.on_conflict_do_update(
                constraint=SOURCE_IDENTITY_CONSTRAINT,
                set_={
                    "socrata_row_id": stmt.excluded.socrata_row_id,
                    "street_name": stmt.excluded.street_name,
                    "borough": stmt.excluded.borough,
                    "postcode": stmt.excluded.postcode,
                    "construction_type": stmt.excluded.construction_type,
                    "num_units": stmt.excluded.num_units,
                    "latitude": stmt.excluded.latitude,
                    "longitude": stmt.excluded.longitude,
                    "last_synced_from_socrata": stmt.excluded.last_synced_from_socrata,
                    "updated_at": func.now(),
                },
            )
            session.execute(stmt)
            total_attempted += len(normalized)

        if by_socrata_id:
            normalized = [
                {**_normalize_source_record(r), "last_synced_from_socrata": now}
                for r in by_socrata_id
            ]
            stmt = pg_insert(HousingUnit).values(normalized)
            stmt = stmt.on_conflict_do_update(
                constraint=SOCRATA_ROW_IDENTITY_CONSTRAINT,
                set_={
                    "project_id": stmt.excluded.project_id,
                    "building_id": stmt.excluded.building_id,
                    "street_name": stmt.excluded.street_name,
                    "borough": stmt.excluded.borough,
                    "postcode": stmt.excluded.postcode,
                    "construction_type": stmt.excluded.construction_type,
                    "num_units": stmt.excluded.num_units,
                    "latitude": stmt.excluded.latitude,
                    "longitude": stmt.excluded.longitude,
                    "last_synced_from_socrata": stmt.excluded.last_synced_from_socrata,
                    "updated_at": func.now(),
                },
            )
            session.execute(stmt)
            total_attempted += len(normalized)

        session.flush()
        logger.info("upserted records from source", extra={"count": total_attempted})
        return total_attempted
    except SQLAlchemyError as exc:
        logger.error("upsert_from_source failed", extra={"error": str(exc)})
        raise


def _normalize_source_record(record: dict[str, Any]) -> dict[str, Any]:
    """Map source field names to internal field names and strip unknown fields.

    Socrata returns ~35 fields; we only persist the ones that have model columns.
    Unknown source fields are silently dropped — this keeps the upsert safe when
    the upstream dataset adds new columns.

    Every returned dict has exactly the same set of keys regardless of what the
    source record contains. Missing source fields become None. This is required
    for SQLAlchemy's batch INSERT — all rows in a VALUES list must share the same
    columns or the compile step raises CompileError.

    Socrata field → internal field:
      total_units                 → num_units (int cast — source sends strings)
      reporting_construction_type → construction_type
      borough                     → borough (uppercased)

    Kept as-is: project_id, building_id, street_name, postcode, latitude, longitude.
    """
    raw_total = record.get("total_units")
    borough = record.get("borough")

    return {
        "project_id": record.get("project_id") or None,
        "building_id": record.get("building_id") or None,
        "socrata_row_id": record.get(":id") or None,
        "street_name": record.get("street_name") or None,
        "postcode": record.get("postcode") or None,
        "latitude": record.get("latitude") or None,
        "longitude": record.get("longitude") or None,
        "num_units": int(raw_total) if raw_total not in (None, "") else 0,
        "construction_type": record.get("reporting_construction_type") or None,
        "borough": borough.upper() if borough else None,
    }


def _has_socrata_row_id(record: dict[str, Any]) -> bool:
    rid = record.get(":id")
    if rid is None:
        return False
    return str(rid).strip() != ""


def _has_complete_source_identity(record: dict[str, Any]) -> bool:
    project_id = record.get("project_id")
    building_id = record.get("building_id")
    if project_id is None or building_id is None:
        return False
    if str(project_id).strip() == "" or str(building_id).strip() == "":
        return False
    return True

def _apply_rectangle_filter(stmt: Any, filters: HousingUnitFilters) -> Any:
    """Apply a bounding box WHERE clause for geo_shape=rectangle."""
    return stmt.where(
        HousingUnit.latitude.between(filters.min_lat, filters.max_lat),
        HousingUnit.longitude.between(filters.min_lon, filters.max_lon),
    )


def _apply_circle_filter(stmt: Any, filters: HousingUnitFilters) -> Any:
    """Apply a bounding box approximation for geo_shape=circle.

    Approximates the circle as a bounding box:
      1 degree latitude  ≈ 111,111 m (constant)
      1 degree longitude ≈ 111,111 * cos(lat) m (varies with latitude)

    This is not a true circle filter — it includes corner points outside the radius.
    It is accurate enough for the MVP without requiring PostGIS.
    A PostGIS ST_DWithin upgrade would be the production path.
    """
    center_lat = float(filters.center_lat)  # type: ignore[arg-type]
    center_lon = float(filters.center_lon)  # type: ignore[arg-type]
    radius_m = float(filters.radius_m)  # type: ignore[arg-type]

    lat_delta = radius_m / _METERS_PER_DEGREE_LAT
    lon_delta = radius_m / (_METERS_PER_DEGREE_LAT * math.cos(math.radians(center_lat)))

    return stmt.where(
        HousingUnit.latitude.between(center_lat - lat_delta, center_lat + lat_delta),
        HousingUnit.longitude.between(center_lon - lon_delta, center_lon + lon_delta),
    )
