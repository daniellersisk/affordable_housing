"""E2E tests for sort, nearby, and analytics summary endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.e2e
def test_sort_by_num_units_desc(client: TestClient, auth_headers: dict) -> None:
    """List sorted by num_units descending returns units in correct order."""
    for n in (10, 50, 25):
        client.post("/v1/housing-units", json={"num_units": n}, headers=auth_headers)

    response = client.get("/v1/housing-units?sort_by=num_units&sort_order=desc&limit=10")
    assert response.status_code == 200
    items = response.json()["items"]
    units = [item["num_units"] for item in items]
    assert units == sorted(units, reverse=True)


@pytest.mark.e2e
def test_sort_by_num_units_asc(client: TestClient, auth_headers: dict) -> None:
    """List sorted by num_units ascending returns units in correct order."""
    for n in (30, 5, 15):
        client.post("/v1/housing-units", json={"num_units": n}, headers=auth_headers)

    response = client.get("/v1/housing-units?sort_by=num_units&sort_order=asc&limit=10")
    assert response.status_code == 200
    items = response.json()["items"]
    units = [item["num_units"] for item in items]
    assert units == sorted(units)


@pytest.mark.e2e
def test_nearby_returns_units_within_radius(client: TestClient, auth_headers: dict) -> None:
    """Nearby returns units within the given radius and excludes the requested unit."""
    # unit with coordinates
    anchor = client.post(
        "/v1/housing-units",
        json={"num_units": 10, "latitude": "40.7128", "longitude": "-74.0060"},
        headers=auth_headers,
    )
    assert anchor.status_code == 201
    anchor_id = anchor.json()["id"]

    # close unit — within 500m
    client.post(
        "/v1/housing-units",
        json={"num_units": 5, "latitude": "40.7130", "longitude": "-74.0055"},
        headers=auth_headers,
    )
    # far unit — outside 500m
    client.post(
        "/v1/housing-units",
        json={"num_units": 5, "latitude": "41.000", "longitude": "-75.000"},
        headers=auth_headers,
    )

    response = client.get(f"/v1/housing-units/{anchor_id}/nearby?radius_m=500")
    assert response.status_code == 200
    items = response.json()["items"]
    ids = [item["id"] for item in items]
    assert anchor_id not in ids


@pytest.mark.e2e
def test_analytics_summary_reflects_created_data(client: TestClient, auth_headers: dict) -> None:
    """Analytics summary total_records increases as records are created."""
    before = client.get("/v1/analytics/summary").json()["total_records"]

    client.post("/v1/housing-units", json={"num_units": 10}, headers=auth_headers)
    client.post("/v1/housing-units", json={"num_units": 20}, headers=auth_headers)

    after = client.get("/v1/analytics/summary").json()["total_records"]
    assert after == before + 2


@pytest.mark.e2e
def test_analytics_summary_units_by_borough(client: TestClient, auth_headers: dict) -> None:
    """Borough breakdown reflects inserted records."""
    client.post(
        "/v1/housing-units",
        json={"num_units": 100, "borough": "MANHATTAN"},
        headers=auth_headers,
    )

    response = client.get("/v1/analytics/summary")
    boroughs = {b["borough"]: b for b in response.json()["units_by_borough"]}
    assert "MANHATTAN" in boroughs
    assert boroughs["MANHATTAN"]["total_units"] >= 100
