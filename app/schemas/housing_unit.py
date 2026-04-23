from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class HousingUnitCreate(BaseModel):
    """Request body for POST /housing-units."""

    street_name: str | None = None
    borough: str | None = None
    postcode: str | None = None
    construction_type: str | None = None
    num_units: int = Field(..., ge=0, description="must be zero or greater")
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    project_id: str | None = None
    building_id: str | None = None


class HousingUnitUpdate(BaseModel):
    """Request body for PUT /housing-units/{id}."""

    street_name: str | None = None
    borough: str | None = None
    postcode: str | None = None
    construction_type: str | None = None
    num_units: int | None = Field(default=None, ge=0)
    latitude: Decimal | None = None
    longitude: Decimal | None = None


class HousingUnitResponse(BaseModel):
    """Response schema for a single housing unit."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: str | None
    building_id: str | None
    street_name: str | None
    borough: str | None
    postcode: str | None
    construction_type: str | None
    num_units: int
    latitude: Decimal | None
    longitude: Decimal | None
    created_at: datetime
    updated_at: datetime


class HousingUnitListResponse(BaseModel):
    """Response schema for GET /housing-units."""

    items: list[HousingUnitResponse]
    total: int
    limit: int
    offset: int


class ErrorDetail(BaseModel):
    """A single structured error detail entry."""

    field: str | None = None
    message: str


class ErrorResponse(BaseModel):
    """Structured error payload returned on all 4xx/5xx responses."""

    code: str
    message: str
    details: list[ErrorDetail] = []
