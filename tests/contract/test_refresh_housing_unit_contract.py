"""Contract tests for POST /v1/housing-units/{id}/refresh.

The Socrata client is mocked in all tests — no real HTTP calls to NYC Open Data.
Tests verify: status codes, response schema, error schema, and auth contract.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

SOCRATA_PATCH = "app.services.housing_unit_service.socrata_client"


def _source_record(project_id: str = "PROJ-1", building_id: str = "BLD-1") -> dict:
    return {
        ":id": "999",
        "project_id": project_id,
        "building_id": building_id,
        "total_units": "42",
        "street_name": "Broadway",
        "borough": "Manhattan",
        "postcode": "10001",
        "reporting_construction_type": "NEW CONSTRUCTION",
    }


def _create_source_unit(
    client: TestClient,
    auth_headers: dict,
    project_id: str = "PROJ-1",
    building_id: str = "BLD-1",
) -> int:
    resp = client.post(
        "/v1/housing-units",
        json={
            "num_units": 10,
            "project_id": project_id,
            "building_id": building_id,
            "street_name": "Old Name",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Auth contract
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_refresh_returns_401_without_auth(client: TestClient) -> None:
    """Missing X-API-Key returns 401 with structured error."""
    response = client.post("/v1/housing-units/1/refresh")
    assert response.status_code == 401
    detail = response.json()["detail"]
    assert detail["code"] == "UNAUTHORIZED"
    assert "details" in detail


@pytest.mark.negative
@pytest.mark.contract
def test_refresh_returns_401_with_invalid_auth(client: TestClient) -> None:
    """Invalid X-API-Key returns 401 with structured error."""
    response = client.post(
        "/v1/housing-units/1/refresh",
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401
    detail = response.json()["detail"]
    assert detail["code"] == "UNAUTHORIZED"


# ---------------------------------------------------------------------------
# Not found
# ---------------------------------------------------------------------------


@pytest.mark.negative
@pytest.mark.contract
def test_refresh_returns_404_for_unknown_id(client: TestClient, auth_headers: dict) -> None:
    """Refreshing a non-existent unit returns 404 with NOT_FOUND code."""
    response = client.post("/v1/housing-units/999999/refresh", headers=auth_headers)
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["code"] == "NOT_FOUND"
    assert "message" in detail
    assert "details" in detail


# ---------------------------------------------------------------------------
# Validation failure — no source identity
# ---------------------------------------------------------------------------


@pytest.mark.negative
@pytest.mark.contract
def test_refresh_returns_422_for_manually_created_unit(
    client: TestClient, auth_headers: dict
) -> None:
    """Unit created manually (no project_id/building_id) returns 422."""
    resp = client.post(
        "/v1/housing-units",
        json={"num_units": 5, "street_name": "Manual St"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    unit_id = resp.json()["id"]

    response = client.post(f"/v1/housing-units/{unit_id}/refresh", headers=auth_headers)
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "VALIDATION_ERROR"
    assert "message" in detail
    assert "details" in detail


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_refresh_returns_200_with_updated_unit(client: TestClient, auth_headers: dict) -> None:
    """Successful refresh returns 200 and the refreshed unit schema."""
    unit_id = _create_source_unit(client, auth_headers)
    mock_client = MagicMock()
    mock_client.get_by_source_id.return_value = _source_record()

    with patch(SOCRATA_PATCH, mock_client):
        response = client.post(f"/v1/housing-units/{unit_id}/refresh", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == unit_id
    assert data["num_units"] == 42
    assert data["street_name"] == "Broadway"
    assert data["borough"] == "MANHATTAN"
    assert data["construction_type"] == "NEW CONSTRUCTION"


@pytest.mark.contract
def test_refresh_response_schema(client: TestClient, auth_headers: dict) -> None:
    """Refresh response contains all required HousingUnitResponse fields."""
    unit_id = _create_source_unit(client, auth_headers)
    mock_client = MagicMock()
    mock_client.get_by_source_id.return_value = _source_record()

    with patch(SOCRATA_PATCH, mock_client):
        response = client.post(f"/v1/housing-units/{unit_id}/refresh", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    for field in ("id", "num_units", "project_id", "building_id", "created_at", "updated_at",
                  "last_synced_from_socrata"):
        assert field in data, f"missing field: {field}"


@pytest.mark.contract
def test_refresh_sets_last_synced_from_socrata(client: TestClient, auth_headers: dict) -> None:
    """last_synced_from_socrata is non-null after a successful refresh."""
    unit_id = _create_source_unit(client, auth_headers)
    mock_client = MagicMock()
    mock_client.get_by_source_id.return_value = _source_record()

    with patch(SOCRATA_PATCH, mock_client):
        response = client.post(f"/v1/housing-units/{unit_id}/refresh", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["last_synced_from_socrata"] is not None


@pytest.mark.negative
@pytest.mark.contract
def test_refresh_returns_404_when_socrata_has_no_record(
    client: TestClient, auth_headers: dict
) -> None:
    """Returns 404 when the unit exists in DB but Socrata returns nothing."""
    unit_id = _create_source_unit(client, auth_headers, project_id="GONE-1", building_id="GONE-B")
    mock_client = MagicMock()
    mock_client.get_by_source_id.return_value = None

    with patch(SOCRATA_PATCH, mock_client):
        response = client.post(f"/v1/housing-units/{unit_id}/refresh", headers=auth_headers)

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["code"] == "NOT_FOUND"
