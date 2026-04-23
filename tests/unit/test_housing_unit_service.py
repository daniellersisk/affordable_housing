from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core.errors import NotFoundError
from app.schemas.filters import HousingUnitFilters
from app.services import housing_unit_service as service

# all tests mock the repository so no DB is needed — service layer is pure python.
MODULE = "app.services.housing_unit_service.repo"


def _make_unit(**kwargs) -> MagicMock:
    """Build a mock HousingUnit with sensible defaults.

    Uses MagicMock rather than a real HousingUnit so unit tests have no
    SQLAlchemy session dependency — the service layer only reads id,
    project_id, and building_id from the returned objects.
    """
    defaults = {"id": 1, "street_name": "Test St", "borough": "MANHATTAN", "num_units": 10,
                "project_id": None, "building_id": None}
    defaults.update(kwargs)
    unit = MagicMock()
    for key, value in defaults.items():
        setattr(unit, key, value)
    return unit


# ---------------------------------------------------------------------------
# get_housing_unit
# ---------------------------------------------------------------------------


def test_get_housing_unit_returns_unit() -> None:
    unit = _make_unit()
    session = MagicMock()
    with patch(f"{MODULE}.get_by_id", return_value=unit):
        result = service.get_housing_unit(session, 1)
    assert result is unit


def test_get_housing_unit_raises_not_found_when_missing() -> None:
    session = MagicMock()
    with patch(f"{MODULE}.get_by_id", return_value=None):
        with pytest.raises(NotFoundError):
            service.get_housing_unit(session, 999)


# ---------------------------------------------------------------------------
# list_housing_units
# ---------------------------------------------------------------------------


def test_list_housing_units_returns_results() -> None:
    units = [_make_unit(id=1), _make_unit(id=2)]
    session = MagicMock()
    filters = HousingUnitFilters(borough="BROOKLYN")
    with patch(f"{MODULE}.list_with_filters", return_value=units) as mock_list:
        result = service.list_housing_units(session, filters)
    assert result == units
    mock_list.assert_called_once_with(session, filters)


def test_list_housing_units_returns_empty_list() -> None:
    session = MagicMock()
    with patch(f"{MODULE}.list_with_filters", return_value=[]):
        result = service.list_housing_units(session, HousingUnitFilters())
    assert result == []


# ---------------------------------------------------------------------------
# create_housing_unit
# ---------------------------------------------------------------------------


def test_create_housing_unit_returns_created_unit() -> None:
    unit = _make_unit()
    session = MagicMock()
    data = {"street_name": "Broadway", "num_units": 50}
    with patch(f"{MODULE}.create", return_value=unit) as mock_create:
        result = service.create_housing_unit(session, data)
    assert result is unit
    mock_create.assert_called_once_with(session, data)


# ---------------------------------------------------------------------------
# update_housing_unit
# ---------------------------------------------------------------------------


def test_update_housing_unit_returns_updated_unit() -> None:
    unit = _make_unit()
    updated = _make_unit(street_name="New St")
    session = MagicMock()
    with patch(f"{MODULE}.get_by_id", return_value=unit), \
         patch(f"{MODULE}.update", return_value=updated):
        result = service.update_housing_unit(session, 1, {"street_name": "New St"})
    assert result is updated


def test_update_housing_unit_raises_not_found() -> None:
    session = MagicMock()
    with patch(f"{MODULE}.get_by_id", return_value=None):
        with pytest.raises(NotFoundError):
            service.update_housing_unit(session, 999, {"num_units": 5})


def test_update_housing_unit_allows_source_managed_rows() -> None:
    """source-managed rows (project_id + building_id set) can be updated freely."""
    unit = _make_unit(project_id="P1", building_id="B1")
    updated = _make_unit(num_units=99)
    session = MagicMock()
    with patch(f"{MODULE}.get_by_id", return_value=unit), \
         patch(f"{MODULE}.update", return_value=updated):
        result = service.update_housing_unit(session, 1, {"num_units": 99})
    assert result is updated


# ---------------------------------------------------------------------------
# delete_housing_unit
# ---------------------------------------------------------------------------


def test_delete_housing_unit_calls_repo_delete() -> None:
    unit = _make_unit()
    session = MagicMock()
    with patch(f"{MODULE}.get_by_id", return_value=unit), \
         patch(f"{MODULE}.delete") as mock_delete:
        service.delete_housing_unit(session, 1)
    mock_delete.assert_called_once_with(session, 1)


def test_delete_housing_unit_raises_not_found() -> None:
    session = MagicMock()
    with patch(f"{MODULE}.get_by_id", return_value=None):
        with pytest.raises(NotFoundError):
            service.delete_housing_unit(session, 999)


def test_delete_housing_unit_allows_source_managed_rows() -> None:
    """source-managed rows (project_id + building_id set) can be deleted freely."""
    unit = _make_unit(project_id="P1", building_id="B1")
    session = MagicMock()
    with patch(f"{MODULE}.get_by_id", return_value=unit), \
         patch(f"{MODULE}.delete") as mock_delete:
        service.delete_housing_unit(session, 1)
    mock_delete.assert_called_once_with(session, 1)
