# Pydantic query parameter schemas for GET /housing-units filtering.
# Geo filter uses a single geo_shape discriminator (rectangle or circle).
# Invalid or mixed geo params must return 422 with code=INVALID_GEO_FILTER.
# Step 5 will implement the full filter model and geo validation logic.
from __future__ import annotations

# TODO: Step 5 - define HousingUnitFilters query model with:
#   street_name, borough, postcode, construction_type (optional strings)
#   num_units_min, num_units_max (optional ints)
#   geo_shape (GeoShape enum, optional)
#   rectangle params: min_lat, max_lat, min_lon, max_lon
#   circle params: center_lat, center_lon, radius_m
#   limit, offset for pagination
# TODO: Step 5 - validator: geo_shape must be set when any geo param is provided
# TODO: Step 5 - add validator that enforces required params per geo_shape value
