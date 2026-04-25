from __future__ import annotations

import math

import pytest

from app.repositories.housing_unit_repository import (
    _METERS_PER_DEGREE_LAT,
    _has_complete_source_identity,
    _has_socrata_row_id,
    _normalize_source_record,
    upsert_from_source,
)

pytestmark = pytest.mark.unit


def test_normalize_source_record_maps_total_units() -> None:
    """total_units is cast to int and mapped to num_units at write time."""
    record = {":id": "1", "project_id": "P1", "building_id": "B1", "total_units": "42"}
    result = _normalize_source_record(record)
    assert result["socrata_row_id"] == "1"
    assert "num_units" in result
    assert result["num_units"] == 42
    assert isinstance(result["num_units"], int)
    assert "total_units" not in result


def test_normalize_source_record_maps_reporting_construction_type() -> None:
    """reporting_construction_type is mapped to construction_type."""
    record = {":id": "1", "project_id": "P1", "building_id": "B1", "total_units": "10",
              "reporting_construction_type": "New Construction"}
    result = _normalize_source_record(record)
    assert result["construction_type"] == "New Construction"
    assert "reporting_construction_type" not in result


def test_normalize_source_record_uppercases_borough() -> None:
    """borough from source ('Queens') is normalized to uppercase ('QUEENS')."""
    record = {":id": "1", "project_id": "P1", "building_id": "B1", "total_units": "10",
              "borough": "Queens"}
    result = _normalize_source_record(record)
    assert result["borough"] == "QUEENS"


def test_normalize_source_record_preserves_other_fields() -> None:
    """Fields not requiring mapping are passed through unchanged."""
    record = {
        ":id": "1",
        "project_id": "P1",
        "building_id": "B1",
        "total_units": "10",
        "street_name": "Broadway",
        "borough": "MANHATTAN",
    }
    result = _normalize_source_record(record)
    assert result["street_name"] == "Broadway"
    assert result["project_id"] == "P1"


def test_normalize_source_record_no_total_units_defaults_num_units_to_zero() -> None:
    """Records without total_units produce num_units=0 and a full fixed-key shape."""
    record = {":id": "1", "project_id": "P1", "building_id": "B1"}
    result = _normalize_source_record(record)
    assert result["num_units"] == 0
    assert result["project_id"] == "P1"
    assert result["building_id"] == "B1"
    # all model keys are always present
    for key in (
        "project_id",
        "building_id",
        "socrata_row_id",
        "street_name",
        "postcode",
        "latitude",
        "longitude",
        "num_units",
        "construction_type",
        "borough",
    ):
        assert key in result


def test_normalize_source_record_does_not_mutate_input() -> None:
    """Original record dict is not mutated."""
    record = {":id": "1", "total_units": 7, "project_id": "P1", "building_id": "B1"}
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


def test_has_socrata_row_id_false_for_none_or_blank() -> None:
    assert _has_socrata_row_id({":id": None}) is False
    assert _has_socrata_row_id({":id": ""}) is False
    assert _has_socrata_row_id({":id": "   "}) is False


def test_has_socrata_row_id_true_for_non_blank() -> None:
    assert _has_socrata_row_id({":id": "1"}) is True
    assert _has_socrata_row_id({":id": 123}) is True
    assert _has_socrata_row_id({":id": "  123  "}) is True


def test_has_complete_source_identity_false_for_missing_or_blank() -> None:
    assert _has_complete_source_identity({"project_id": None, "building_id": "B"}) is False
    assert _has_complete_source_identity({"project_id": "P", "building_id": None}) is False
    assert _has_complete_source_identity({"project_id": "", "building_id": "B"}) is False
    assert _has_complete_source_identity({"project_id": "   ", "building_id": "B"}) is False
    assert _has_complete_source_identity({"project_id": "P", "building_id": ""}) is False
    assert _has_complete_source_identity({"project_id": "P", "building_id": "   "}) is False


def test_has_complete_source_identity_true_for_non_blank() -> None:
    assert _has_complete_source_identity({"project_id": "P1", "building_id": "B1"}) is True
    assert _has_complete_source_identity({"project_id": 1, "building_id": 2}) is True


class _ExplodeOnEq:
    def __eq__(self, other: object) -> bool:  # noqa: ANN001
        raise AssertionError("dict equality should not be used for partitioning")


class _FakeSession:
    def __init__(self) -> None:
        self.executed: int = 0

    class _Result:
        def all(self) -> list[object]:
            return []

    def execute(self, stmt: object) -> _Result:  # noqa: ANN401
        self.executed += 1
        return self._Result()

    def flush(self) -> None:
        return None


def test_upsert_from_source_partitions_without_dict_equality() -> None:
    """Guard against O(n*m) dict-equality partitioning.

    This test would fail if remainder partitioning used `r not in by_source_identity`,
    because that triggers dict equality (including value `__eq__`) comparisons.
    """
    records = [
        {
            ":id": "s1",
            "project_id": "P1",
            "building_id": "B1",
            "total_units": "10",
            "boom": _ExplodeOnEq(),
        },
        {
            ":id": "s2",
            # missing composite identity -> should flow into socrata-id upsert path
            "total_units": "5",
            "boom": _ExplodeOnEq(),
        },
    ]

    session = _FakeSession()
    attempted = upsert_from_source(session, records)  # type: ignore[arg-type]
    assert attempted == 2
    # 1 read for socrata conflict detection + up to 2 upsert statements
    assert session.executed >= 2
