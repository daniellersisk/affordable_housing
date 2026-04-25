"""Contract tests for GET /housing-units."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.contract
def test_get_housing_units_success_contract(client: TestClient) -> None:
    """200 with correct list response schema."""
    response = client.get("/v1/housing-units")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["items"], list)
    # total is the full matching count (not just current page length)
    assert isinstance(data["total"], int)
    assert data["total"] >= len(data["items"])


@pytest.mark.contract
def test_get_housing_units_pagination_contract(client: TestClient) -> None:
    """limit and offset query params are reflected in response."""
    response = client.get("/v1/housing-units?limit=5&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 5
    assert data["offset"] == 0
    assert data["total"] >= len(data["items"])


@pytest.mark.contract
def test_get_housing_units_geo_params_without_shape_returns_422(client: TestClient) -> None:
    """geo params without geo_shape return 422 with INVALID_GEO_FILTER code."""
    response = client.get("/v1/housing-units?min_lat=40.6")
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "INVALID_GEO_FILTER"
    assert "message" in detail


@pytest.mark.contract
def test_get_housing_units_rectangle_missing_params_returns_422(client: TestClient) -> None:
    """rectangle shape with missing params returns 422."""
    response = client.get("/v1/housing-units?geo_shape=rectangle&min_lat=40.6")
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "INVALID_GEO_FILTER"


@pytest.mark.contract
def test_get_housing_units_item_schema_contract(client: TestClient) -> None:
    """each item in the list has the required response fields."""
    response = client.get("/v1/housing-units")
    assert response.status_code == 200
    items = response.json()["items"]
    if items:
        item = items[0]
        for field in ("id", "num_units", "created_at", "updated_at"):
            assert field in item
