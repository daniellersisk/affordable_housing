from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.constants import GeoShape
from app.schemas.filters import HousingUnitFilters
from app.schemas.housing_unit import HousingUnitCreate, HousingUnitUpdate

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# HousingUnitFilters — geo validation
# ---------------------------------------------------------------------------


def test_filters_no_geo_params_valid() -> None:
    f = HousingUnitFilters(borough="BROOKLYN")
    assert f.borough == "BROOKLYN"
    assert f.geo_shape is None


def test_filters_geo_params_without_geo_shape_raises() -> None:
    with pytest.raises(ValidationError) as exc_info:
        HousingUnitFilters(min_lat=Decimal("40.6"))
    errors = exc_info.value.errors()
    assert errors[0]["type"] == "invalid_geo_filter"


def test_filters_rectangle_all_params_valid() -> None:
    f = HousingUnitFilters(
        geo_shape=GeoShape.RECTANGLE,
        min_lat=Decimal("40.6"),
        max_lat=Decimal("40.8"),
        min_lon=Decimal("-74.1"),
        max_lon=Decimal("-73.9"),
    )
    assert f.geo_shape == GeoShape.RECTANGLE


def test_filters_rectangle_missing_param_raises() -> None:
    with pytest.raises(ValidationError) as exc_info:
        HousingUnitFilters(
            geo_shape=GeoShape.RECTANGLE,
            min_lat=Decimal("40.6"),
            max_lat=Decimal("40.8"),
        )
    errors = exc_info.value.errors()
    assert errors[0]["type"] == "invalid_geo_filter"


def test_filters_circle_all_params_valid() -> None:
    f = HousingUnitFilters(
        geo_shape=GeoShape.CIRCLE,
        center_lat=Decimal("40.7128"),
        center_lon=Decimal("-74.0060"),
        radius_m=500.0,
    )
    assert f.geo_shape == GeoShape.CIRCLE


def test_filters_circle_missing_radius_raises() -> None:
    with pytest.raises(ValidationError) as exc_info:
        HousingUnitFilters(
            geo_shape=GeoShape.CIRCLE,
            center_lat=Decimal("40.7128"),
            center_lon=Decimal("-74.0060"),
        )
    errors = exc_info.value.errors()
    assert errors[0]["type"] == "invalid_geo_filter"


def test_filters_rectangle_with_extra_circle_params_raises() -> None:
    with pytest.raises(ValidationError) as exc_info:
        HousingUnitFilters(
            geo_shape=GeoShape.RECTANGLE,
            min_lat=Decimal("40.6"),
            max_lat=Decimal("40.8"),
            min_lon=Decimal("-74.1"),
            max_lon=Decimal("-73.9"),
            center_lat=Decimal("40.7"),
        )
    errors = exc_info.value.errors()
    assert errors[0]["type"] == "invalid_geo_filter"


def test_filters_circle_with_extra_rectangle_params_raises() -> None:
    with pytest.raises(ValidationError) as exc_info:
        HousingUnitFilters(
            geo_shape=GeoShape.CIRCLE,
            center_lat=Decimal("40.7128"),
            center_lon=Decimal("-74.0060"),
            radius_m=500.0,
            min_lat=Decimal("40.6"),
        )
    errors = exc_info.value.errors()
    assert errors[0]["type"] == "invalid_geo_filter"


def test_filters_pagination_defaults() -> None:
    f = HousingUnitFilters()
    assert f.limit == 100
    assert f.offset == 0


# ---------------------------------------------------------------------------
# HousingUnitCreate — field validation
# ---------------------------------------------------------------------------


def test_create_valid_minimal() -> None:
    body = HousingUnitCreate(num_units=10)
    assert body.num_units == 10


def test_create_negative_num_units_raises() -> None:
    with pytest.raises(ValidationError):
        HousingUnitCreate(num_units=-1)


def test_create_invalid_borough_raises() -> None:
    with pytest.raises(ValidationError):
        HousingUnitCreate(num_units=10, borough="NEW JERSEY")


def test_create_valid_borough() -> None:
    body = HousingUnitCreate(num_units=10, borough="MANHATTAN")
    assert body.borough == "MANHATTAN"


def test_create_street_name_too_long_raises() -> None:
    with pytest.raises(ValidationError):
        HousingUnitCreate(num_units=10, street_name="A" * 201)


def test_create_postcode_non_numeric_raises() -> None:
    with pytest.raises(ValidationError):
        HousingUnitCreate(num_units=10, postcode="1001A")


def test_create_postcode_numeric_valid() -> None:
    body = HousingUnitCreate(num_units=10, postcode="10001")
    assert body.postcode == "10001"


def test_update_postcode_non_numeric_raises() -> None:
    with pytest.raises(ValidationError):
        HousingUnitUpdate(postcode="abc")


def test_filters_postcode_non_numeric_raises() -> None:
    with pytest.raises(ValidationError):
        HousingUnitFilters(postcode="10001A")


def test_create_zero_num_units_valid() -> None:
    body = HousingUnitCreate(num_units=0)
    assert body.num_units == 0


def test_create_all_fields() -> None:
    body = HousingUnitCreate(
        street_name="Broadway",
        borough="MANHATTAN",
        postcode="10001",
        construction_type="NEW CONSTRUCTION",
        num_units=50,
        latitude=Decimal("40.7128"),
        longitude=Decimal("-74.0060"),
        project_id="P1",
        building_id="B1",
    )
    assert body.street_name == "Broadway"
    assert body.project_id == "P1"


# ---------------------------------------------------------------------------
# HousingUnitUpdate — partial update semantics
# ---------------------------------------------------------------------------


def test_update_all_optional() -> None:
    body = HousingUnitUpdate()
    assert body.num_units is None
    assert body.street_name is None


def test_update_negative_num_units_raises() -> None:
    with pytest.raises(ValidationError):
        HousingUnitUpdate(num_units=-5)


def test_update_exclude_unset_only_sends_provided_fields() -> None:
    body = HousingUnitUpdate(street_name="New St")
    data = body.model_dump(exclude_unset=True)
    assert "street_name" in data
    assert "num_units" not in data
