# Service layer for housing unit business logic.
# Orchestrates repository calls, enforces domain rules, and raises typed errors.
# Route handlers call services; services call repositories.
# Never import FastAPI or HTTP concerns here.
# Step 4 will implement the full service methods.
from __future__ import annotations

# TODO: Step 4 - implement get_housing_unit(session, id) -> HousingUnit
# TODO: Step 4 - implement list_housing_units(session, filters) -> list[HousingUnit]
# TODO: Step 4 - implement create_housing_unit(session, data) -> HousingUnit
# TODO: Step 4 - implement update_housing_unit(session, id, data) -> HousingUnit
#   raise ConflictError for source-managed rows
# TODO: Step 4 - implement delete_housing_unit(session, id) -> None
#   raise ConflictError for source-managed rows
