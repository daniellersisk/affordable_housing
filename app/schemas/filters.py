from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from app.core.constants import Borough, GeoShape, SortField, SortOrder

Latitude = Annotated[Decimal, Field(ge=Decimal("-90.000000"), le=Decimal("90.000000"))]
Longitude = Annotated[Decimal, Field(ge=Decimal("-180.000000"), le=Decimal("180.000000"))]

# pydantic model used for both route-level query param parsing/validation
# and repository filter composition. the model_validator enforces that
# geo_shape is set whenever any geo param is provided, and that the
# required params for each shape are present.


class HousingUnitFilters(BaseModel):
    """Query parameters for GET /housing-units."""

    street_name: str | None = None
    borough: Borough | None = None
    postcode: str | None = None
    construction_type: str | None = None
    num_units_min: int | None = Field(default=None, ge=1)
    num_units_max: int | None = Field(default=None, ge=1)

    geo_shape: GeoShape | None = None

    # rectangle params
    min_lat: Latitude | None = None
    max_lat: Latitude | None = None
    min_lon: Longitude | None = None
    max_lon: Longitude | None = None

    # circle params
    center_lat: Latitude | None = None
    center_lon: Longitude | None = None
    radius_m: float | None = None

    # sorting
    sort_by: SortField = SortField.ID
    sort_order: SortOrder = SortOrder.ASC

    # pagination
    limit: int = 100
    offset: int = 0

    @field_validator("borough", mode="before")
    @classmethod
    def normalize_borough(cls, v: str | None) -> str | None:
        return v.upper() if v is not None else v

    @field_validator("postcode")
    @classmethod
    def postcode_digits_only(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.isdigit():
            raise ValueError("postcode must contain digits only")
        if len(v) != 5:
            raise ValueError("postcode must be exactly 5 digits")
        return v

    @model_validator(mode="after")
    def validate_num_units_range(self) -> HousingUnitFilters:
        if (
            self.num_units_min is not None
            and self.num_units_max is not None
            and self.num_units_min > self.num_units_max
        ):
            raise PydanticCustomError(
                "invalid_num_units_range",
                "num_units_min must be less than or equal to num_units_max",
            )
        return self

    @model_validator(mode="after")
    def validate_geo(self) -> HousingUnitFilters:
        rectangle_params = {"min_lat", "max_lat", "min_lon", "max_lon"}
        circle_params = {"center_lat", "center_lon", "radius_m"}
        geo_params = rectangle_params | circle_params
        provided_geo = [f for f in geo_params if getattr(self, f) is not None]

        if provided_geo and self.geo_shape is None:
            raise PydanticCustomError(
                "invalid_geo_filter",
                "geo_shape is required when any geo param is provided",
            )

        if self.geo_shape == GeoShape.RECTANGLE:
            extra = [f for f in circle_params if getattr(self, f) is not None]
            if extra:
                raise PydanticCustomError(
                    "invalid_geo_filter",
                    f"rectangle does not allow circle params: {', '.join(sorted(extra))}",
                )
            missing = [
                f for f in ("min_lat", "max_lat", "min_lon", "max_lon")
                if getattr(self, f) is None
            ]
            if missing:
                raise PydanticCustomError(
                    "invalid_geo_filter",
                    f"rectangle requires: {', '.join(missing)}",
                )

        if self.geo_shape == GeoShape.CIRCLE:
            extra = [f for f in rectangle_params if getattr(self, f) is not None]
            if extra:
                raise PydanticCustomError(
                    "invalid_geo_filter",
                    f"circle does not allow rectangle params: {', '.join(sorted(extra))}",
                )
            missing = [
                f for f in ("center_lat", "center_lon", "radius_m")
                if getattr(self, f) is None
            ]
            if missing:
                raise PydanticCustomError(
                    "invalid_geo_filter",
                    f"circle requires: {', '.join(missing)}",
                )

        return self
