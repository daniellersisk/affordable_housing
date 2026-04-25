from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_write_auth
from app.core.constants import ErrorCode, GeoShape, SortField, SortOrder
from app.core.errors import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.schemas.filters import HousingUnitFilters
from app.schemas.housing_unit import (
    HousingUnitCreate,
    HousingUnitListResponse,
    HousingUnitResponse,
    HousingUnitUpdate,
)
from app.services import housing_unit_service as service

logger = get_logger(__name__)

# public endpoints — no auth required, read-only
public_router = APIRouter(
    prefix="/v1/housing-units",
    tags=["housing-units — public"],
)

# private endpoints — X-API-Key required, write operations
private_router = APIRouter(
    prefix="/v1/housing-units",
    tags=["housing-units — private"],
)


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


# ---------------------------------------------------------------------------
# public routes
# ---------------------------------------------------------------------------


@public_router.get("", response_model=HousingUnitListResponse)
def list_housing_units(
    street_name: str | None = Query(default=None),
    borough: str | None = Query(default=None),
    postcode: str | None = Query(default=None),
    construction_type: str | None = Query(default=None),
    num_units_min: int | None = Query(default=None, ge=1),
    num_units_max: int | None = Query(default=None, ge=0),
    geo_shape: GeoShape | None = Query(default=None),
    min_lat: float | None = Query(default=None),
    max_lat: float | None = Query(default=None),
    min_lon: float | None = Query(default=None),
    max_lon: float | None = Query(default=None),
    center_lat: float | None = Query(default=None),
    center_lon: float | None = Query(default=None),
    radius_m: float | None = Query(default=None),
    sort_by: SortField = Query(default=SortField.ID),
    sort_order: SortOrder = Query(default=SortOrder.ASC),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
) -> HousingUnitListResponse:
    """List housing units with optional filters, sorting, and pagination."""
    logger.info("GET /v1/housing-units")
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
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
        )
    except ValidationError as exc:
        first = exc.errors()[0]
        code = (
            ErrorCode.INVALID_GEO_FILTER
            if first.get("type") == "invalid_geo_filter"
            else ErrorCode.VALIDATION_ERROR
        )
        clean_msg = first.get("msg", "validation error")
        raise HTTPException(
            status_code=422,
            detail={"code": code, "message": clean_msg, "details": []},
        ) from exc

    units = service.list_housing_units(session, filters)
    total = service.count_housing_units(session, filters)
    return HousingUnitListResponse(
        items=[HousingUnitResponse.model_validate(u) for u in units],
        total=total,
        limit=limit,
        offset=offset,
    )


@public_router.get("/{unit_id}", response_model=HousingUnitResponse)
def get_housing_unit(
    unit_id: int,
    session: Session = Depends(get_db),
) -> HousingUnitResponse:
    """Fetch a single housing unit by id."""
    logger.info("GET /v1/housing-units/%s", unit_id)
    try:
        unit = service.get_housing_unit(session, unit_id)
    except NotFoundError:
        raise _not_found(unit_id)
    return HousingUnitResponse.model_validate(unit)


@public_router.get("/{unit_id}/nearby", response_model=HousingUnitListResponse)
def get_nearby_housing_units(
    unit_id: int,
    radius_m: float = Query(..., gt=0, description="search radius in metres"),
    limit: int = Query(default=10, ge=1, le=100),
    response: Response = None,  # type: ignore[assignment]
    session: Session = Depends(get_db),
) -> HousingUnitListResponse:
    """Return housing units within approximately radius_m metres of the given unit.

    **Geo approximation:** uses a bounding-box (rectangle) approximation for the
    circle filter. Points in the corners of the bounding box that fall outside the
    true radius may be included. The response carries an
    `X-Geo-Approximation: bounding-box` header to make this explicit.
    PostGIS `ST_DWithin` would provide exact circle results in production.

    Returns 404 if the unit does not exist or has no coordinates.
    The requested unit is excluded from results.
    """
    logger.info("GET /v1/housing-units/%s/nearby", unit_id)
    try:
        unit = service.get_housing_unit(session, unit_id)
    except NotFoundError:
        raise _not_found(unit_id)

    if unit.latitude is None or unit.longitude is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": ErrorCode.NOT_FOUND,
                "message": f"housing unit {unit_id} has no coordinates — nearby unavailable",
                "details": [],
            },
        )

    nearby_filters = HousingUnitFilters(
        geo_shape=GeoShape.CIRCLE,
        center_lat=unit.latitude,
        center_lon=unit.longitude,
        radius_m=radius_m,
        limit=limit + 1,  # fetch one extra to allow excluding self
        offset=0,
    )
    results = service.list_housing_units(session, nearby_filters)
    nearby = [u for u in results if u.id != unit_id][:limit]

    if response is not None:
        response.headers["X-Geo-Approximation"] = "bounding-box"

    return HousingUnitListResponse(
        items=[HousingUnitResponse.model_validate(u) for u in nearby],
        total=len(nearby),
        limit=limit,
        offset=0,
    )


# ---------------------------------------------------------------------------
# private routes
# ---------------------------------------------------------------------------


@private_router.post("", response_model=HousingUnitResponse, status_code=status.HTTP_201_CREATED)
def create_housing_unit(
    body: HousingUnitCreate,
    session: Session = Depends(get_db),
    _auth: None = Depends(require_write_auth),
) -> HousingUnitResponse:
    """Create a new housing unit."""
    logger.info("POST /v1/housing-units")
    try:
        unit = service.create_housing_unit(session, body.model_dump(exclude_none=False))
        session.commit()
    except ConflictError as exc:
        raise _conflict(str(exc))
    return HousingUnitResponse.model_validate(unit)


@private_router.put("/{unit_id}", response_model=HousingUnitResponse)
def update_housing_unit(
    unit_id: int,
    body: HousingUnitUpdate,
    session: Session = Depends(get_db),
    _auth: None = Depends(require_write_auth),
) -> HousingUnitResponse:
    """Update a housing unit by id."""
    logger.info("PUT /v1/housing-units/%s", unit_id)
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


@private_router.delete("/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_housing_unit(
    unit_id: int,
    session: Session = Depends(get_db),
    _auth: None = Depends(require_write_auth),
) -> None:
    """Delete a housing unit by id."""
    logger.info("DELETE /v1/housing-units/%s", unit_id)
    try:
        service.delete_housing_unit(session, unit_id)
        session.commit()
    except NotFoundError:
        raise _not_found(unit_id)


@private_router.post("/{unit_id}/refresh", response_model=HousingUnitResponse)
def refresh_housing_unit(
    unit_id: int,
    session: Session = Depends(get_db),
    _auth: None = Depends(require_write_auth),
) -> HousingUnitResponse:
    """Re-sync one existing record from Socrata using its stored source identity.

    Returns 404 if the unit does not exist.
    Returns 422 if the unit has no source identity (was created manually via POST).
    """
    logger.info("POST /v1/housing-units/%s/refresh", unit_id)
    try:
        unit = service.get_housing_unit(session, unit_id)
    except NotFoundError:
        raise _not_found(unit_id)

    if not unit.project_id or not unit.building_id:
        raise HTTPException(
            status_code=422,
            detail={
                "code": ErrorCode.VALIDATION_ERROR,
                "message": f"housing unit {unit_id} has no source identity — cannot refresh",
                "details": [],
            },
        )

    try:
        refreshed = service.sync_from_source(session, unit.project_id, unit.building_id)
        session.commit()
    except NotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "code": ErrorCode.NOT_FOUND,
                "message": str(exc),
                "details": [],
            },
        )
    logger.info("POST /v1/housing-units/%s/refresh complete", unit_id)
    return HousingUnitResponse.model_validate(refreshed)
