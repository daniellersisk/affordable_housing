# SQLAlchemy ORM model for the housing_units table.
# This model is the persistence representation of a housing unit record.
# API request/response shapes live in app/schemas, not here.
# Step 3 will implement the full column definitions and constraints.
from __future__ import annotations

# TODO: Step 3 - define HousingUnit ORM model with all required columns:
#   id (BIGSERIAL or UUID primary key)
#   project_id, building_id (source identity, composite unique constraint)
#   street_name, borough, postcode, construction_type (indexed)
#   num_units (int, non-negative; mapped from source total_units)
#   latitude, longitude (optional)
#   created_at, updated_at
