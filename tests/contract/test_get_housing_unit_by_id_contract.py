"""Contract tests for GET /housing-units/{id}."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.contract
def test_get_housing_unit_by_id_success_contract(client: TestClient, auth_headers: dict) -> None:
    """200 with correct single unit schema after creating one."""
    created = client.post(
        "/v1/housing-units",
        json={"num_units": 10, "street_name": "Contract St"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    unit_id = created.json()["id"]

    response = client.get(f"/v1/housing-units/{unit_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == unit_id
    assert data["street_name"] == "Contract St"
    assert data["num_units"] == 10
    for field in ("id", "num_units", "created_at", "updated_at"):
        assert field in data


@pytest.mark.negative
@pytest.mark.contract
def test_get_housing_unit_by_id_not_found_contract(client: TestClient) -> None:
    """404 with structured error schema for missing id."""
    response = client.get("/v1/housing-units/999999999")
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["code"] == "NOT_FOUND"
    assert "message" in detail
    assert "details" in detail
