"""Contract tests for POST /housing-units."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.contract
def test_post_housing_unit_success_contract(client: TestClient, auth_headers: dict) -> None:
    """201 with full response schema on valid payload."""
    response = client.post(
        "/housing-units",
        json={"num_units": 25, "street_name": "Post St", "borough": "BROOKLYN"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["num_units"] == 25
    assert data["street_name"] == "Post St"
    assert data["borough"] == "BROOKLYN"
    for field in ("id", "num_units", "created_at", "updated_at"):
        assert field in data


@pytest.mark.contract
def test_post_housing_unit_auth_error_contract(client: TestClient) -> None:
    """401 with structured error schema when no auth header provided."""
    response = client.post("/housing-units", json={"num_units": 10})
    assert response.status_code == 401
    detail = response.json()["detail"]
    assert detail["code"] == "UNAUTHORIZED"
    assert "message" in detail
    assert "details" in detail


@pytest.mark.contract
def test_post_housing_unit_wrong_key_returns_401(client: TestClient) -> None:
    """401 when wrong api key is provided."""
    response = client.post(
        "/housing-units",
        json={"num_units": 10},
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401


@pytest.mark.contract
def test_post_housing_unit_validation_error_contract(
    client: TestClient, auth_headers: dict
) -> None:
    """422 when num_units is negative."""
    response = client.post(
        "/housing-units",
        json={"num_units": -1},
        headers=auth_headers,
    )
    assert response.status_code == 422
