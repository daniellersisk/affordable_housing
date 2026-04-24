"""Contract tests for bonus endpoints: sort, nearby, analytics summary."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.contract
def test_list_sort_by_num_units_desc_contract(client: TestClient, auth_headers: dict) -> None:
    """sort_by=num_units&sort_order=desc returns 200 with correct schema."""
    response = client.get("/v1/housing-units?sort_by=num_units&sort_order=desc")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    items = data["items"]
    if len(items) >= 2:
        assert items[0]["num_units"] >= items[1]["num_units"]


@pytest.mark.contract
def test_list_invalid_sort_field_returns_422(client: TestClient) -> None:
    """invalid sort_by value returns 422."""
    response = client.get("/v1/housing-units?sort_by=invalid_field")
    assert response.status_code == 422


@pytest.mark.contract
def test_nearby_no_coordinates_returns_404(client: TestClient, auth_headers: dict) -> None:
    """nearby returns 404 when unit has no coordinates."""
    created = client.post(
        "/v1/housing-units",
        json={"num_units": 5, "street_name": "No Coords St"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    unit_id = created.json()["id"]

    response = client.get(f"/v1/housing-units/{unit_id}/nearby?radius_m=500")
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["code"] == "NOT_FOUND"
    assert "no coordinates" in detail["message"] or "nearby" in detail["message"]


@pytest.mark.contract
def test_nearby_missing_radius_returns_422(client: TestClient) -> None:
    """nearby without radius_m returns 422."""
    response = client.get("/v1/housing-units/1/nearby")
    assert response.status_code == 422


@pytest.mark.contract
def test_analytics_summary_success_contract(client: TestClient) -> None:
    """GET /v1/analytics/summary returns 200 with correct schema."""
    response = client.get("/v1/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_units" in data
    assert "total_records" in data
    assert "units_by_borough" in data
    assert "top_construction_types" in data
    assert isinstance(data["total_units"], int)
    assert isinstance(data["total_records"], int)
    assert isinstance(data["units_by_borough"], list)
    assert isinstance(data["top_construction_types"], list)


@pytest.mark.contract
def test_analytics_summary_borough_schema(client: TestClient, auth_headers: dict) -> None:
    """borough entries in summary have required fields."""
    client.post(
        "/v1/housing-units",
        json={"num_units": 10, "borough": "BROOKLYN"},
        headers=auth_headers,
    )
    response = client.get("/v1/analytics/summary")
    assert response.status_code == 200
    boroughs = response.json()["units_by_borough"]
    if boroughs:
        b = boroughs[0]
        assert "total_units" in b
        assert "record_count" in b
