from __future__ import annotations

import math

from app.repositories.housing_unit_repository import (
    _METERS_PER_DEGREE_LAT,
    _normalize_source_record,
)


def test_normalize_source_record_maps_total_units() -> None:
    """total_units is mapped to num_units at write time."""
    record = {"project_id": "P1", "building_id": "B1", "total_units": 42}
    result = _normalize_source_record(record)
    assert "num_units" in result
    assert result["num_units"] == 42
    assert "total_units" not in result


def test_normalize_source_record_preserves_other_fields() -> None:
    """Fields other than total_units are passed through unchanged."""
    record = {
        "project_id": "P1",
        "building_id": "B1",
        "total_units": 10,
        "street_name": "Broadway",
        "borough": "MANHATTAN",
    }
    result = _normalize_source_record(record)
    assert result["street_name"] == "Broadway"
    assert result["borough"] == "MANHATTAN"
    assert result["project_id"] == "P1"


def test_normalize_source_record_no_total_units_unchanged() -> None:
    """Records without total_units are returned as-is."""
    record = {"project_id": "P1", "building_id": "B1", "num_units": 5}
    result = _normalize_source_record(record)
    assert result == record


def test_normalize_source_record_does_not_mutate_input() -> None:
    """Original record dict is not mutated."""
    record = {"total_units": 7, "project_id": "P1", "building_id": "B1"}
    original = dict(record)
    _normalize_source_record(record)
    assert record == original


def test_circle_bounding_box_lat_delta() -> None:
    """1 degree lat ≈ 111,111 m — radius_m / _METERS_PER_DEGREE_LAT gives lat delta."""
    radius_m = 1000.0
    expected_lat_delta = radius_m / _METERS_PER_DEGREE_LAT
    assert abs(expected_lat_delta - 0.009) < 0.001


def test_circle_bounding_box_lon_delta_varies_with_latitude() -> None:
    """Longitude delta is larger near the equator, smaller near the poles."""
    radius_m = 1000.0
    lat_equator = 0.0
    lat_nyc = 40.7128

    lon_delta_equator = radius_m / (_METERS_PER_DEGREE_LAT * math.cos(math.radians(lat_equator)))
    lon_delta_nyc = radius_m / (_METERS_PER_DEGREE_LAT * math.cos(math.radians(lat_nyc)))

    # near nyc (higher latitude) the lon delta should be larger because
    # longitude lines converge toward the poles
    assert lon_delta_nyc > lon_delta_equator
