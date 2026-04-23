from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_write_auth
from app.core.constants import ErrorCode, GeoShape
from app.core.errors import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.schemas.filters import HousingUnitFilters
from app.schemas.housing_unit import (
    ErrorResponse,
    HousingUnitCreate,
    HousingUnitListResponse,
    HousingUnitResponse,
    HousingUnitUpdate,
)
from app.services import housing_unit_service as service

logger = get_logger(__name__)

router = APIRouter(prefix="/housing-units", tags=["housing-units"])


def _not_found(unit_id: int) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={
            "code": ErrorCode.NOT_FOUND,
            "message": f"housing unit {unit_id} not found",
            "details": [],
        },
    )


def _conflict(message: str) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={
            "code": ErrorCode.CONFLICT,
            "message": message,
            "details": [],
        },
    )


def _invalid_geo(message: str) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={
            "code": ErrorCode.INVALID_GEO_FILTER,
            "message": message,
            "details": [],
        },
    )


@router.get("", response_model=HousingUnitListResponse)
def list_housing_units(
    street_name: str | None = Query(default=None),
    borough: str | None = Query(default=None),
    postcode: str | None = Query(default=None),
    construction_type: str | None = Query(default=None),
    num_units_min: int | None = Query(default=None, ge=0),
    num_units_max: int | None = Query(default=None, ge=0),
    geo_shape: GeoShape | None = Query(default=None),
    min_lat: float | None = Query(default=None),
    max_lat: float | None = Query(default=None),
    min_lon: float | None = Query(default=None),
    max_lon: float | None = Query(default=None),
    center_lat: float | None = Query(default=None),
    center_lon: float | None = Query(default=None),
    radius_m: float | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
) -> HousingUnitListResponse:
    """List housing units with optional filters and pagination."""
    logger.info("GET /housing-units")
    try:
        filters = HousingUnitFilters(
            street_name=street_name,
            borough=borough,
            postcode=postcode,
            construction_type=construction_type,
            num_units_min=num_units_min,
            num_units_max=num_units_max,
            geo_shape=geo_shape,
            min_lat=min_lat,
            max_lat=max_lat,
            min_lon=min_lon,
            max_lon=max_lon,
            center_lat=center_lat,
            center_lon=center_lon,
            radius_m=radius_m,
            limit=limit,
            offset=offset,
        )
    except ValidationError as exc:
        first = exc.errors()[0]
        msg = first["msg"].removeprefix("Value error, ")
        is_geo = "INVALID_GEO_FILTER" in msg
        code = ErrorCode.INVALID_GEO_FILTER if is_geo else ErrorCode.VALIDATION_ERROR
        clean_msg = msg.split("|")[0]
        raise HTTPException(
            status_code=422,
            detail={"code": code, "message": clean_msg, "details": []},
        ) from exc

    units = service.list_housing_units(session, filters)
    return HousingUnitListResponse(
        items=[HousingUnitResponse.model_validate(u) for u in units],
        total=len(units),
        limit=limit,
        offset=offset,
    )


@router.get("/{unit_id}", response_model=HousingUnitResponse)
def get_housing_unit(
    unit_id: int,
    session: Session = Depends(get_db),
) -> HousingUnitResponse:
    """Fetch a single housing unit by id."""
    logger.info("GET /housing-units/%s", unit_id)
    try:
        unit = service.get_housing_unit(session, unit_id)
    except NotFoundError:
        raise _not_found(unit_id)
    return HousingUnitResponse.model_validate(unit)


@router.post("", response_model=HousingUnitResponse, status_code=status.HTTP_201_CREATED)
def create_housing_unit(
    body: HousingUnitCreate,
    session: Session = Depends(get_db),
    _auth: None = Depends(require_write_auth),
) -> HousingUnitResponse:
    """Create a new housing unit."""
    logger.info("POST /housing-units")
    try:
        unit = service.create_housing_unit(session, body.model_dump(exclude_none=False))
        session.commit()
    except ConflictError as exc:
        raise _conflict(str(exc))
    return HousingUnitResponse.model_validate(unit)


@router.put("/{unit_id}", response_model=HousingUnitResponse)
def update_housing_unit(
    unit_id: int,
    body: HousingUnitUpdate,
    session: Session = Depends(get_db),
    _auth: None = Depends(require_write_auth),
) -> HousingUnitResponse:
    """Update a housing unit by id."""
    logger.info("PUT /housing-units/%s", unit_id)
    try:
        unit = service.update_housing_unit(
            session, unit_id, body.model_dump(exclude_unset=True)
        )
        session.commit()
    except NotFoundError:
        raise _not_found(unit_id)
    except ConflictError as exc:
        raise _conflict(str(exc))
    return HousingUnitResponse.model_validate(unit)


@router.delete("/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_housing_unit(
    unit_id: int,
    session: Session = Depends(get_db),
    _auth: None = Depends(require_write_auth),
) -> None:
    """Delete a housing unit by id."""
    logger.info("DELETE /housing-units/%s", unit_id)
    try:
        service.delete_housing_unit(session, unit_id)
        session.commit()
    except NotFoundError:
        raise _not_found(unit_id)


@router.post("/{unit_id}/refresh", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def refresh_housing_unit(
    unit_id: int,
    _auth: None = Depends(require_write_auth),
) -> ErrorResponse:
    """Re-sync one record from Socrata. Implemented in Phase 4."""
    logger.info("POST /housing-units/%s/refresh (not yet implemented)", unit_id)
    return ErrorResponse(
        code="NOT_IMPLEMENTED",
        message="refresh endpoint will be available once the Socrata client is implemented",
        details=[],
    )


@router.post("/sync", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def sync_housing_unit(
    _auth: None = Depends(require_write_auth),
) -> ErrorResponse:
    """Sync a record from Socrata by source identity. Implemented in Phase 4."""
    logger.info("POST /housing-units/sync (not yet implemented)")
    return ErrorResponse(
        code="NOT_IMPLEMENTED",
        message="sync endpoint will be available once the Socrata client is implemented",
        details=[],
    )
