"""Unit tests for SocrataClient.

All HTTP calls are mocked — no real network requests are made.
Tests verify pagination, single-record lookup, SoQL injection escaping, and retry logic.
"""
from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import httpx
import pytest

from app.clients.socrata_client import SocrataClient, _escape_soql
from app.settings import Settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SETTINGS = Settings(
    nyc_open_data_base_url="https://data.cityofnewyork.us",
    nyc_open_data_view_id="hg8x-zxpr",
    soda_app_token="test-token",
    ingest_page_size=2,
    ingest_timeout_seconds=5,
    ingest_max_retries=3,
)

_RECORD_A = {"project_id": "P1", "building_id": "B1", "total_units": "10"}
_RECORD_B = {"project_id": "P2", "building_id": "B2", "total_units": "20"}
_RECORD_C = {"project_id": "P3", "building_id": "B3", "total_units": "30"}


def _mock_response(data: list[dict], status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = data
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# get_all — pagination
# ---------------------------------------------------------------------------


def test_get_all_yields_pages_until_empty() -> None:
    """get_all stops when Socrata returns an empty page."""
    client = SocrataClient(_SETTINGS)
    responses = [
        _mock_response([_RECORD_A, _RECORD_B]),
        _mock_response([]),
    ]
    with patch("httpx.get", side_effect=responses):
        pages = list(client.get_all())
    assert pages == [[_RECORD_A, _RECORD_B]]


def test_get_all_stops_on_partial_last_page() -> None:
    """get_all stops when the last page has fewer records than page_size."""
    client = SocrataClient(_SETTINGS)
    responses = [
        _mock_response([_RECORD_A, _RECORD_B]),
        _mock_response([_RECORD_C]),  # only 1 record < page_size of 2
    ]
    with patch("httpx.get", side_effect=responses):
        pages = list(client.get_all())
    assert len(pages) == 2
    assert pages[0] == [_RECORD_A, _RECORD_B]
    assert pages[1] == [_RECORD_C]


def test_get_all_advances_offset_correctly() -> None:
    """Each successive page request uses the correct $offset param."""
    client = SocrataClient(_SETTINGS)
    responses = [
        _mock_response([_RECORD_A, _RECORD_B]),
        _mock_response([]),
    ]
    with patch("httpx.get", side_effect=responses) as mock_get:
        list(client.get_all())

    first_params = mock_get.call_args_list[0].kwargs["params"]
    second_params = mock_get.call_args_list[1].kwargs["params"]
    assert first_params["$offset"] == "0"
    assert second_params["$offset"] == "2"


def test_get_all_sends_app_token_header() -> None:
    """App token is included in the X-App-Token header."""
    client = SocrataClient(_SETTINGS)
    with patch("httpx.get", return_value=_mock_response([])) as mock_get:
        list(client.get_all())
    headers = mock_get.call_args.kwargs["headers"]
    assert headers.get("X-App-Token") == "test-token"


def test_get_all_omits_app_token_header_when_empty() -> None:
    """No X-App-Token header is sent when soda_app_token is not configured."""
    cfg = Settings(
        nyc_open_data_base_url="https://data.cityofnewyork.us",
        nyc_open_data_view_id="hg8x-zxpr",
        soda_app_token="",
        ingest_page_size=2,
        ingest_timeout_seconds=5,
        ingest_max_retries=3,
    )
    client = SocrataClient(cfg)
    with patch("httpx.get", return_value=_mock_response([])) as mock_get:
        list(client.get_all())
    headers = mock_get.call_args.kwargs["headers"]
    assert "X-App-Token" not in headers


# ---------------------------------------------------------------------------
# get_by_source_id
# ---------------------------------------------------------------------------


def test_get_by_source_id_returns_first_result() -> None:
    client = SocrataClient(_SETTINGS)
    with patch("httpx.get", return_value=_mock_response([_RECORD_A])):
        result = client.get_by_source_id("P1", "B1")
    assert result == _RECORD_A


def test_get_by_source_id_returns_none_when_empty() -> None:
    client = SocrataClient(_SETTINGS)
    with patch("httpx.get", return_value=_mock_response([])):
        result = client.get_by_source_id("MISSING", "MISSING")
    assert result is None


def test_get_by_source_id_query_contains_identifiers() -> None:
    """The $where param sent to Socrata references the supplied project_id and building_id."""
    client = SocrataClient(_SETTINGS)
    with patch("httpx.get", return_value=_mock_response([])) as mock_get:
        client.get_by_source_id("PROJ-1", "BLDG-1")
    where = mock_get.call_args.kwargs["params"]["$where"]
    assert "PROJ-1" in where
    assert "BLDG-1" in where


# ---------------------------------------------------------------------------
# SoQL injection prevention
# ---------------------------------------------------------------------------


def test_escape_soql_doubles_single_quotes() -> None:
    assert _escape_soql("O'Malley") == "O''Malley"


def test_escape_soql_leaves_safe_strings_unchanged() -> None:
    assert _escape_soql("PROJ-123") == "PROJ-123"


def test_get_by_source_id_escapes_single_quotes_in_query() -> None:
    """Single quotes in identifiers must be escaped before embedding in the $where param."""
    client = SocrataClient(_SETTINGS)
    with patch("httpx.get", return_value=_mock_response([])) as mock_get:
        client.get_by_source_id("O'Reilly", "B'1")
    where = mock_get.call_args.kwargs["params"]["$where"]
    assert "O''Reilly" in where
    assert "B''1" in where
    # Raw unescaped quotes must not appear adjacent to the value
    assert "='O'Reilly'" not in where


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------


def test_retries_on_transient_5xx_then_succeeds() -> None:
    """Client retries on 5xx and succeeds on the third attempt."""
    client = SocrataClient(_SETTINGS)
    fail = _mock_response([], status_code=503)
    ok = _mock_response([_RECORD_A])
    with patch("httpx.get", side_effect=[fail, fail, ok]):
        with patch("time.sleep"):
            result = client.get_by_source_id("P1", "B1")
    assert result == _RECORD_A


def test_raises_after_max_retries_exceeded() -> None:
    """Client raises HTTPStatusError after exhausting all retries."""
    client = SocrataClient(_SETTINGS)
    fail = _mock_response([], status_code=503)
    with patch("httpx.get", side_effect=[fail, fail, fail]):
        with patch("time.sleep"):
            with pytest.raises(httpx.HTTPStatusError):
                client.get_by_source_id("P1", "B1")


def test_does_not_retry_on_4xx() -> None:
    """Client does not retry on 4xx client errors — they are permanent."""
    client = SocrataClient(_SETTINGS)
    fail_400 = _mock_response([], status_code=400)
    with patch("httpx.get", side_effect=[fail_400]) as mock_get:
        with patch("time.sleep"):
            with pytest.raises(httpx.HTTPStatusError):
                client.get_by_source_id("P1", "B1")
    assert mock_get.call_count == 1
