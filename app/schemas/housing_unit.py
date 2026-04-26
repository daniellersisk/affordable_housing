from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import Borough

# latitude and longitude are stored as Numeric(9,6) in postgres — 9 total digits, 6 after
# the decimal point. valid ranges are -90/90 for lat and -180/180 for lon.
#
# they are returned as Decimal strings in json responses (e.g. "40.712800") rather than
# floats. this is intentional: python floats lose precision for geographic coordinates
# (e.g. 40.7128 stored as float may round to 40.71280000000001 in json). Decimal
# preserves the exact value as stored in the DB.
#
# consumers reading the API should parse latitude/longitude as float or Decimal —
# both work. the extra string precision is harmless and avoids silent rounding bugs.
Latitude = Annotated[Decimal, Field(ge=Decimal("-90.000000"), le=Decimal("90.000000"))]
Longitude = Annotated[Decimal, Field(ge=Decimal("-180.000000"), le=Decimal("180.000000"))]


def _validate_postcode(value: str | None) -> str | None:
    if value is None:
        return value
    if not value.isdigit():
        raise ValueError("postcode must contain digits only")
    if len(value) != 5:
        raise ValueError("postcode must be exactly 5 digits")
    return value


class HousingUnitCreate(BaseModel):
    """Request body for POST /housing-units."""

    street_name: str | None = Field(default=None, max_length=200)
    borough: Borough | None = None
    postcode: str | None = None
    construction_type: str | None = None
    num_units: int = Field(..., ge=0, description="must be zero or greater")
    latitude: Latitude | None = None
    longitude: Longitude | None = None
    project_id: str | None = None
    building_id: str | None = None

    @field_validator("borough", mode="before")
    @classmethod
    def normalize_borough(cls, v: str | None) -> str | None:
        return v.upper() if v is not None else v

    @field_validator("postcode")
    @classmethod
    def postcode_digits_only(cls, v: str | None) -> str | None:
        return _validate_postcode(v)


class HousingUnitUpdate(BaseModel):
    """Request body for PUT /housing-units/{id}."""

    street_name: str | None = Field(default=None, max_length=200)
    borough: Borough | None = None
    postcode: str | None = None
    construction_type: str | None = None
    num_units: int | None = Field(default=None, ge=0)
    latitude: Latitude | None = None
    longitude: Longitude | None = None

    @field_validator("borough", mode="before")
    @classmethod
    def normalize_borough(cls, v: str | None) -> str | None:
        return v.upper() if v is not None else v

    @field_validator("postcode")
    @classmethod
    def postcode_digits_only(cls, v: str | None) -> str | None:
        return _validate_postcode(v)


class HousingUnitResponse(BaseModel):
    """Response schema for a single housing unit."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 799523655,
                    "project_id": "PROJ-1",
                    "building_id": "BLD-1",
                    "street_name": "Broadway",
                    "borough": "MANHATTAN",
                    "postcode": "10001",
                    "construction_type": "NEW CONSTRUCTION",
                    "num_units": 42,
                    "latitude": "40.712800",
                    "longitude": "-74.006000",
                    "created_at": "2026-04-26T20:06:30.114Z",
                    "updated_at": "2026-04-26T20:06:30.114Z",
                    "last_synced_from_socrata": "2026-04-26T20:06:30.114Z",
                }
            ]
        },
    )

    id: int
    project_id: str | None
    building_id: str | None
    street_name: str | None
    borough: str | None  # str not Borough enum — reads must not fail on legacy/imported values
    postcode: str | None
    construction_type: str | None
    num_units: int
    latitude: Latitude | None
    longitude: Longitude | None
    created_at: datetime
    updated_at: datetime
    last_synced_from_socrata: datetime | None


class HousingUnitListResponse(BaseModel):
    """Response schema for GET /housing-units."""

    items: list[HousingUnitResponse]
    total: int = Field(
        ...,
        description=(
            "Total number of records matching the provided filters (ignores limit/offset)."
        ),
    )
    limit: int
    offset: int

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items": [
                        {
                            "id": 1,
                            "project_id": None,
                            "building_id": None,
                            "street_name": "Lifecycle Ave",
                            "borough": "QUEENS",
                            "postcode": None,
                            "construction_type": None,
                            "num_units": 20,
                            "latitude": None,
                            "longitude": None,
                            "created_at": "2026-04-26T20:06:30.114Z",
                            "updated_at": "2026-04-26T20:06:30.114Z",
                            "last_synced_from_socrata": None,
                        }
                    ],
                    "total": 1,
                    "limit": 100,
                    "offset": 0,
                }
            ]
        }
    )
