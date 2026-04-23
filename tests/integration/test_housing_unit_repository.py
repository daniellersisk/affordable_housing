from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.constants import GeoShape
from app.core.errors import ConflictError, NotFoundError
from app.models.housing_unit import HousingUnit
from app.repositories import housing_unit_repository as repo
from app.schemas.filters import HousingUnitFilters


def _make_unit(session: Session, **kwargs) -> HousingUnit:
    """Helper: insert and flush a housing unit with sensible defaults."""
    defaults = {"street_name": "Test St", "borough": "MANHATTAN", "num_units": 10}
    defaults.update(kwargs)
    unit = HousingUnit(**defaults)
    session.add(unit)
    session.flush()
    return unit


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_get_by_id_returns_unit(db_session: Session) -> None:
    unit = _make_unit(db_session)
    fetched = repo.get_by_id(db_session, unit.id)
    assert fetched is not None
    assert fetched.id == unit.id


@pytest.mark.integration
def test_get_by_id_returns_none_for_missing(db_session: Session) -> None:
    result = repo.get_by_id(db_session, 999_999_999)
    assert result is None


# ---------------------------------------------------------------------------
# list_with_filters
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_list_with_filters_no_filters_returns_all(db_session: Session) -> None:
    _make_unit(db_session, street_name="Alpha St")
    _make_unit(db_session, street_name="Beta Ave")
    results = repo.list_with_filters(db_session, HousingUnitFilters())
    assert len(results) >= 2


@pytest.mark.integration
def test_list_with_filters_by_borough(db_session: Session) -> None:
    _make_unit(db_session, borough="BROOKLYN")
    _make_unit(db_session, borough="QUEENS")
    results = repo.list_with_filters(db_session, HousingUnitFilters(borough="BROOKLYN"))
    assert all(r.borough == "BROOKLYN" for r in results)


@pytest.mark.integration
def test_list_with_filters_borough_is_uppercased(db_session: Session) -> None:
    """list_with_filters uppercases the borough value before filtering."""
    _make_unit(db_session, borough="BRONX")
    results = repo.list_with_filters(db_session, HousingUnitFilters(borough="bronx"))
    assert any(r.borough == "BRONX" for r in results)


@pytest.mark.integration
def test_list_with_filters_street_name_case_insensitive(db_session: Session) -> None:
    _make_unit(db_session, street_name="Broadway")
    results = repo.list_with_filters(db_session, HousingUnitFilters(street_name="broadway"))
    assert any(r.street_name == "Broadway" for r in results)


@pytest.mark.integration
def test_list_with_filters_num_units_min(db_session: Session) -> None:
    _make_unit(db_session, num_units=5)
    _make_unit(db_session, num_units=50)
    results = repo.list_with_filters(db_session, HousingUnitFilters(num_units_min=20))
    assert all(r.num_units >= 20 for r in results)


@pytest.mark.integration
def test_list_with_filters_num_units_max(db_session: Session) -> None:
    _make_unit(db_session, num_units=5)
    _make_unit(db_session, num_units=50)
    results = repo.list_with_filters(db_session, HousingUnitFilters(num_units_max=10))
    assert all(r.num_units <= 10 for r in results)


@pytest.mark.integration
def test_list_with_filters_num_units_range(db_session: Session) -> None:
    _make_unit(db_session, num_units=5)
    _make_unit(db_session, num_units=20)
    _make_unit(db_session, num_units=100)
    results = repo.list_with_filters(
        db_session, HousingUnitFilters(num_units_min=10, num_units_max=50)
    )
    assert all(10 <= r.num_units <= 50 for r in results)
    assert len(results) >= 1


@pytest.mark.integration
def test_list_with_filters_geo_rectangle(db_session: Session) -> None:
    _make_unit(db_session, latitude=Decimal("40.700"), longitude=Decimal("-73.900"))
    _make_unit(db_session, latitude=Decimal("41.000"), longitude=Decimal("-74.500"))

    results = repo.list_with_filters(
        db_session,
        HousingUnitFilters(
            geo_shape=GeoShape.RECTANGLE,
            min_lat=Decimal("40.600"),
            max_lat=Decimal("40.800"),
            min_lon=Decimal("-74.000"),
            max_lon=Decimal("-73.800"),
        ),
    )
    assert all(
        Decimal("40.600") <= r.latitude <= Decimal("40.800")
        and Decimal("-74.000") <= r.longitude <= Decimal("-73.800")
        for r in results
    )


@pytest.mark.integration
def test_list_with_filters_geo_circle(db_session: Session) -> None:
    # inside ~1km of center
    _make_unit(db_session, latitude=Decimal("40.7128"), longitude=Decimal("-74.0060"))
    # far outside
    _make_unit(db_session, latitude=Decimal("41.000"), longitude=Decimal("-75.000"))

    results = repo.list_with_filters(
        db_session,
        HousingUnitFilters(
            geo_shape=GeoShape.CIRCLE,
            center_lat=Decimal("40.7128"),
            center_lon=Decimal("-74.0060"),
            radius_m=500.0,
        ),
    )
    assert any(abs(float(r.latitude) - 40.7128) < 0.01 for r in results)


@pytest.mark.integration
def test_list_with_filters_pagination(db_session: Session) -> None:
    for i in range(5):
        _make_unit(db_session, street_name=f"Street {i}")

    page1 = repo.list_with_filters(db_session, HousingUnitFilters(limit=2, offset=0))
    page2 = repo.list_with_filters(db_session, HousingUnitFilters(limit=2, offset=2))

    assert len(page1) == 2
    assert len(page2) == 2
    assert {r.id for r in page1}.isdisjoint({r.id for r in page2})


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_create_inserts_unit(db_session: Session) -> None:
    unit = repo.create(
        db_session, {"street_name": "Canal St", "borough": "MANHATTAN", "num_units": 30}
    )
    assert unit.id is not None
    assert unit.street_name == "Canal St"
    assert unit.num_units == 30


@pytest.mark.integration
def test_create_raises_conflict_on_duplicate_source_ids(db_session: Session) -> None:
    repo.create(
        db_session,
        {"project_id": "P1", "building_id": "B1", "num_units": 10},
    )
    db_session.flush()
    with pytest.raises(ConflictError):
        repo.create(
            db_session,
            {"project_id": "P1", "building_id": "B1", "num_units": 20},
        )


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_update_modifies_unit(db_session: Session) -> None:
    unit = _make_unit(db_session, street_name="Old St", num_units=10)
    updated = repo.update(db_session, unit.id, {"street_name": "New St", "num_units": 99})
    assert updated.street_name == "New St"
    assert updated.num_units == 99


@pytest.mark.integration
def test_update_raises_not_found(db_session: Session) -> None:
    with pytest.raises(NotFoundError):
        repo.update(db_session, 999_999_999, {"num_units": 5})


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_delete_removes_unit(db_session: Session) -> None:
    unit = _make_unit(db_session)
    unit_id = unit.id
    repo.delete(db_session, unit_id)
    assert repo.get_by_id(db_session, unit_id) is None


@pytest.mark.integration
def test_delete_raises_not_found(db_session: Session) -> None:
    with pytest.raises(NotFoundError):
        repo.delete(db_session, 999_999_999)


# ---------------------------------------------------------------------------
# upsert_from_source
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_upsert_from_source_inserts_new_records(db_session: Session) -> None:
    records = [
        {"project_id": "P10", "building_id": "B10", "num_units": 15, "borough": "QUEENS"},
        {"project_id": "P11", "building_id": "B11", "num_units": 25, "borough": "BRONX"},
    ]
    count = repo.upsert_from_source(db_session, records)
    assert count == 2


@pytest.mark.integration
def test_upsert_from_source_normalizes_total_units(db_session: Session) -> None:
    """total_units from source is normalized to num_units at write time."""
    records = [{"project_id": "P20", "building_id": "B20", "total_units": 42}]
    repo.upsert_from_source(db_session, records)

    results = repo.list_with_filters(
        db_session, HousingUnitFilters(num_units_min=42, num_units_max=42)
    )
    assert any(r.project_id == "P20" for r in results)


@pytest.mark.integration
def test_upsert_from_source_is_idempotent(db_session: Session) -> None:
    """Re-running upsert on same source ids does not create duplicate rows."""
    records = [{"project_id": "P30", "building_id": "B30", "num_units": 10}]
    repo.upsert_from_source(db_session, records)

    updated_records = [{"project_id": "P30", "building_id": "B30", "num_units": 99}]
    repo.upsert_from_source(db_session, updated_records)

    results = repo.list_with_filters(db_session, HousingUnitFilters())
    matching = [r for r in results if r.project_id == "P30" and r.building_id == "B30"]
    assert len(matching) == 1
    assert matching[0].num_units == 99


@pytest.mark.integration
def test_upsert_from_source_empty_list_returns_zero(db_session: Session) -> None:
    count = repo.upsert_from_source(db_session, [])
    assert count == 0
