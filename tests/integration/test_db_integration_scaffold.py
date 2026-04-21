from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models.housing_unit import HousingUnit


@pytest.mark.integration
def test_housing_unit_insert_assigns_id(db_session: Session) -> None:
    """Insert a HousingUnit row, flush to get the DB-assigned id, and read it back."""
    unit = HousingUnit(street_name="Broadway", borough="MANHATTAN", num_units=50)
    db_session.add(unit)
    db_session.flush()

    assert unit.id is not None
    assert unit.id > 0


@pytest.mark.integration
def test_housing_unit_read_after_flush(db_session: Session) -> None:
    """Verify that a flushed record is visible within the same session."""
    unit = HousingUnit(
        street_name="Atlantic Ave",
        borough="BROOKLYN",
        postcode="11217",
        construction_type="NEW CONSTRUCTION",
        num_units=20,
    )
    db_session.add(unit)
    db_session.flush()

    fetched = db_session.get(HousingUnit, unit.id)

    assert fetched is not None
    assert fetched.street_name == "Atlantic Ave"
    assert fetched.borough == "BROOKLYN"
    assert fetched.postcode == "11217"
    assert fetched.construction_type == "NEW CONSTRUCTION"
    assert fetched.num_units == 20
    assert fetched.created_at is not None
    assert fetched.updated_at is not None


@pytest.mark.integration
def test_housing_unit_num_units_non_negative_constraint(db_session: Session) -> None:
    """Verify the DB-level CHECK constraint rejects negative num_units."""
    from sqlalchemy.exc import IntegrityError

    unit = HousingUnit(num_units=-1)
    db_session.add(unit)
    with pytest.raises(IntegrityError):
        db_session.flush()
