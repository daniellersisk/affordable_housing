# NYC Open Data import script.
# Run explicitly after migrations:
#   docker compose run --rm api python -m app.scripts.import_nyc_data
# Fetches all records from the Socrata dataset using the shared client.
# Normalises source fields (total_units -> num_units) before persistence.
# Uses idempotent upsert so rerunning does not duplicate records.
# Step 6 will implement the full import logic.
from __future__ import annotations

# TODO: Step 6 - implement main() that:
#   instantiates SocrataClient from settings
#   paginates through all source records
#   normalises each record at write-time
#   upserts via housing_unit_repository.upsert_from_source()
#   logs progress and final count
