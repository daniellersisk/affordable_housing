from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.core.constants import GeoShape

# plain dataclass — used by repository and service layers.
# step 5 will add the pydantic model on top for route-level validation and parsing.
# keeping this as a dataclass keeps the repo and service layers framework-independent.


@dataclass
class HousingUnitFilters:
    street_name: str | None = None
    borough: str | None = None
    postcode: str | None = None
    construction_type: str | None = None
    num_units_min: int | None = None
    num_units_max: int | None = None

    # geo discriminator — must be set when any geo param is provided
    geo_shape: GeoShape | None = None

    # rectangle params — required when geo_shape=rectangle
    min_lat: Decimal | None = None
    max_lat: Decimal | None = None
    min_lon: Decimal | None = None
    max_lon: Decimal | None = None

    # circle params — required when geo_shape=circle
    center_lat: Decimal | None = None
    center_lon: Decimal | None = None
    radius_m: float | None = None

    # pagination
    limit: int = field(default=100)
    offset: int = field(default=0)
