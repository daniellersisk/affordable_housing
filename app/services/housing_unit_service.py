from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.models.housing_unit import HousingUnit
from app.repositories import housing_unit_repository as repo
from app.schemas.filters import HousingUnitFilters

logger = get_logger(__name__)

# no fastapi or http imports here — service layer is pure python business logic.
# route handlers call services; services call repositories.
# domain errors raised here are caught and mapped to http responses in the route layer.

# all rows support full crud regardless of source identity.
# source-managed rows (project_id + building_id set) are imported from nyc open data
# but can still be edited or deleted via the api — nearly all data will be source-managed
# so blocking writes on those rows would make put/delete effectively unusable.
# if a recurring import is added in future, the trade-off can be revisited.


def get_housing_unit(session: Session, unit_id: int) -> HousingUnit:
    """Fetch a single housing unit by id. Raises NotFoundError if not found."""
    logger.info("get_housing_unit", extra={"unit_id": unit_id})
    unit = repo.get_by_id(session, unit_id)
    if unit is None:
        raise NotFoundError(f"housing unit {unit_id} not found")
    return unit


def list_housing_units(session: Session, filters: HousingUnitFilters) -> list[HousingUnit]:
    """Return housing units matching the provided filters."""
    logger.info("list_housing_units", extra={"filters": str(filters)})
    return repo.list_with_filters(session, filters)


def create_housing_unit(session: Session, data: dict[str, Any]) -> HousingUnit:
    """Create a new housing unit. Returns the created unit with its assigned id."""
    logger.info("create_housing_unit")
    return repo.create(session, data)


def update_housing_unit(session: Session, unit_id: int, data: dict[str, Any]) -> HousingUnit:
    """Update a housing unit by id. Raises NotFoundError if the unit does not exist."""
    logger.info("update_housing_unit", extra={"unit_id": unit_id})
    unit = repo.get_by_id(session, unit_id)
    if unit is None:
        raise NotFoundError(f"housing unit {unit_id} not found")
    return repo.update(session, unit_id, data)


def delete_housing_unit(session: Session, unit_id: int) -> None:
    """Delete a housing unit by id. Raises NotFoundError if the unit does not exist."""
    logger.info("delete_housing_unit", extra={"unit_id": unit_id})
    unit = repo.get_by_id(session, unit_id)
    if unit is None:
        raise NotFoundError(f"housing unit {unit_id} not found")
    repo.delete(session, unit_id)
