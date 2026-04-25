"""Contract tests for PUT /housing-units/{id}."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.contract
def test_put_housing_unit_success_contract(client: TestClient, auth_headers: dict) -> None:
    """200 with updated response schema."""
    created = client.post(
        "/v1/housing-units",
        json={"num_units": 10, "street_name": "Old St"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    unit_id = created.json()["id"]

    response = client.put(
        f"/v1/housing-units/{unit_id}",
        json={"street_name": "New St"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == unit_id
    assert data["street_name"] == "New St"
    for field in ("id", "num_units", "created_at", "updated_at"):
        assert field in data


@pytest.mark.negative
@pytest.mark.contract
def test_put_housing_unit_auth_error_contract(client: TestClient) -> None:
    """401 with structured error when no auth header provided."""
    response = client.put("/v1/housing-units/1", json={"street_name": "X"})
    assert response.status_code == 401
    detail = response.json()["detail"]
    assert detail["code"] == "UNAUTHORIZED"
    assert "message" in detail
    assert "details" in detail


@pytest.mark.negative
@pytest.mark.contract
def test_put_housing_unit_wrong_key_returns_401(client: TestClient) -> None:
    """401 when wrong api key is provided."""
    response = client.put(
        "/v1/housing-units/1",
        json={"street_name": "X"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401
    detail = response.json()["detail"]
    assert detail["code"] == "UNAUTHORIZED"


@pytest.mark.negative
@pytest.mark.contract
def test_put_housing_unit_not_found_contract(client: TestClient, auth_headers: dict) -> None:
    """404 with structured error for missing id."""
    response = client.put(
        "/v1/housing-units/999999999",
        json={"street_name": "Ghost St"},
        headers=auth_headers,
    )
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["code"] == "NOT_FOUND"
    assert "message" in detail
    assert "details" in detail


@pytest.mark.negative
@pytest.mark.contract
def test_put_housing_unit_validation_error_contract(
    client: TestClient, auth_headers: dict
) -> None:
    """422 when payload fails validation."""
    created = client.post(
        "/v1/housing-units",
        json={"num_units": 10, "street_name": "Valid St"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    unit_id = created.json()["id"]

    response = client.put(
        f"/v1/housing-units/{unit_id}",
        json={"num_units": -1},
        headers=auth_headers,
    )
    assert response.status_code == 422
