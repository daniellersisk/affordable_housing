"""Contract tests for DELETE /housing-units/{id}."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.contract
def test_delete_housing_unit_success_contract(client: TestClient, auth_headers: dict) -> None:
    """204 with empty body on successful delete."""
    created = client.post(
        "/v1/housing-units",
        json={"num_units": 5, "street_name": "Delete Me St"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    unit_id = created.json()["id"]

    response = client.delete(f"/v1/housing-units/{unit_id}", headers=auth_headers)
    assert response.status_code == 204
    assert response.content == b""


@pytest.mark.negative
@pytest.mark.contract
def test_delete_housing_unit_auth_error_contract(client: TestClient) -> None:
    """401 with structured error when no auth header provided."""
    response = client.delete("/v1/housing-units/1")
    assert response.status_code == 401
    detail = response.json()["detail"]
    assert detail["code"] == "UNAUTHORIZED"
    assert "message" in detail
    assert "details" in detail


@pytest.mark.negative
@pytest.mark.contract
def test_delete_housing_unit_wrong_key_returns_401(client: TestClient) -> None:
    """401 when wrong api key is provided."""
    response = client.delete(
        "/v1/housing-units/1",
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401
    detail = response.json()["detail"]
    assert detail["code"] == "UNAUTHORIZED"


@pytest.mark.negative
@pytest.mark.contract
def test_delete_housing_unit_not_found_contract(client: TestClient, auth_headers: dict) -> None:
    """404 with structured error for missing id."""
    response = client.delete("/v1/housing-units/999999999", headers=auth_headers)
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["code"] == "NOT_FOUND"
    assert "message" in detail
    assert "details" in detail
