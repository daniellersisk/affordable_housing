from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.constants import GeoShape

# pydantic model used for both route-level query param parsing/validation
# and repository filter composition. the model_validator enforces that
# geo_shape is set whenever any geo param is provided, and that the
# required params for each shape are present.


class HousingUnitFilters(BaseModel):
    """Query parameters for GET /housing-units."""

    street_name: str | None = None
    borough: str | None = None
    postcode: str | None = None
    construction_type: str | None = None
    num_units_min: int | None = Field(default=None, ge=1)
    num_units_max: int | None = Field(default=None, ge=0)

    geo_shape: GeoShape | None = None

    # rectangle params
    min_lat: Decimal | None = None
    max_lat: Decimal | None = None
    min_lon: Decimal | None = None
    max_lon: Decimal | None = None

    # circle params
    center_lat: Decimal | None = None
    center_lon: Decimal | None = None
    radius_m: float | None = None

    # pagination
    limit: int = 100
    offset: int = 0

    @field_validator("postcode")
    @classmethod
    def postcode_digits_only(cls, v: str | None) -> str | None:
        if v is not None and not v.isdigit():
            raise ValueError("postcode must contain digits only")
        return v

    @model_validator(mode="after")
    def validate_geo(self) -> HousingUnitFilters:
        geo_params = {
            "min_lat", "max_lat", "min_lon", "max_lon",
            "center_lat", "center_lon", "radius_m",
        }
        provided_geo = [f for f in geo_params if getattr(self, f) is not None]

        if provided_geo and self.geo_shape is None:
            raise ValueError(
                "geo_shape is required when any geo param is provided|INVALID_GEO_FILTER"
            )

        if self.geo_shape == GeoShape.RECTANGLE:
            missing = [
                f for f in ("min_lat", "max_lat", "min_lon", "max_lon")
                if getattr(self, f) is None
            ]
            if missing:
                raise ValueError(
                    f"rectangle requires: {', '.join(missing)}|INVALID_GEO_FILTER"
                )

        if self.geo_shape == GeoShape.CIRCLE:
            missing = [
                f for f in ("center_lat", "center_lon", "radius_m")
                if getattr(self, f) is None
            ]
            if missing:
                raise ValueError(
                    f"circle requires: {', '.join(missing)}|INVALID_GEO_FILTER"
                )

        return self
