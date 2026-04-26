from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.repositories import analytics_repository as repo

pytestmark = pytest.mark.unit


class _ResultOne:
    def __init__(self, row: tuple[object, object]) -> None:
        self._row = row

    def one(self) -> tuple[object, object]:
        return self._row


class _ResultAll:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows


def test_get_summary_aggregates_all_components() -> None:
    session = MagicMock()

    totals = _ResultOne((123, 7))
    by_borough = _ResultAll(
        [
            SimpleNamespace(borough="MANHATTAN", total_units=100, record_count=3),
            SimpleNamespace(borough="BROOKLYN", total_units=23, record_count=4),
        ]
    )
    top_types = _ResultAll(
        [
            SimpleNamespace(construction_type="NEW CONSTRUCTION", record_count=5),
            SimpleNamespace(construction_type="PRESERVATION", record_count=2),
        ]
    )

    # get_summary() calls execute() three times: totals, borough group, top types
    session.execute.side_effect = [totals, by_borough, top_types]

    summary = repo.get_summary(session, top_construction_types=2)

    assert summary.total_units == 123
    assert summary.total_records == 7
    assert len(summary.units_by_borough) == 2
    assert summary.units_by_borough[0].borough == "MANHATTAN"
    assert summary.units_by_borough[0].total_units == 100
    assert summary.units_by_borough[0].record_count == 3
    assert len(summary.top_construction_types) == 2
    assert summary.top_construction_types[0].construction_type == "NEW CONSTRUCTION"
    assert summary.top_construction_types[0].record_count == 5


def test_get_summary_coerces_numeric_results_to_int() -> None:
    session = MagicMock()

    totals = _ResultOne(("42", "9"))  # simulate driver returning numeric-ish values
    by_borough = _ResultAll([SimpleNamespace(borough=None, total_units="10", record_count="2")])
    top_types = _ResultAll([SimpleNamespace(construction_type=None, record_count="2")])
    session.execute.side_effect = [totals, by_borough, top_types]

    summary = repo.get_summary(session, top_construction_types=3)

    assert summary.total_units == 42
    assert summary.total_records == 9
    assert summary.units_by_borough[0].total_units == 10
    assert summary.units_by_borough[0].record_count == 2
    assert summary.top_construction_types[0].record_count == 2


def test_get_summary_propagates_sqlalchemy_errors() -> None:
    session = MagicMock()
    session.execute.side_effect = SQLAlchemyError("boom")

    with pytest.raises(SQLAlchemyError):
        repo.get_summary(session, top_construction_types=3)
