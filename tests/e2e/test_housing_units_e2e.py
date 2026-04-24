"""E2E tests for the housing units API.

Tests call the API over HTTP via TestClient — no direct service or
repository calls. Each test exercises a complete lifecycle flow.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.e2e
def test_create_read_update_delete_lifecycle(client: TestClient, auth_headers: dict) -> None:
    """Full CRUD lifecycle: create → read → update → delete → confirm gone."""
    # create
    created = client.post(
        "/v1/housing-units",
        json={"num_units": 20, "street_name": "Lifecycle Ave", "borough": "QUEENS"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    unit = created.json()
    unit_id = unit["id"]
    assert unit["street_name"] == "Lifecycle Ave"

    # read back
    fetched = client.get(f"/v1/housing-units/{unit_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == unit_id

    # update
    updated = client.put(
        f"/v1/housing-units/{unit_id}",
        json={"street_name": "Updated Ave", "num_units": 99},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["street_name"] == "Updated Ave"
    assert updated.json()["num_units"] == 99

    # delete
    deleted = client.delete(f"/v1/housing-units/{unit_id}", headers=auth_headers)
    assert deleted.status_code == 204

    # confirm gone
    gone = client.get(f"/v1/housing-units/{unit_id}")
    assert gone.status_code == 404


@pytest.mark.e2e
def test_list_filters_by_borough(client: TestClient, auth_headers: dict) -> None:
    """Created records are filterable by borough."""
    client.post(
        "/v1/housing-units",
        json={"num_units": 10, "borough": "BRONX"},
        headers=auth_headers,
    )
    client.post(
        "/v1/housing-units",
        json={"num_units": 10, "borough": "STATEN ISLAND"},
        headers=auth_headers,
    )

    response = client.get("/v1/housing-units?borough=BRONX")
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(item["borough"] == "BRONX" for item in items)


@pytest.mark.e2e
def test_list_filters_by_num_units_range(client: TestClient, auth_headers: dict) -> None:
    """num_units_min and num_units_max filter correctly."""
    client.post("/v1/housing-units", json={"num_units": 5}, headers=auth_headers)
    client.post("/v1/housing-units", json={"num_units": 50}, headers=auth_headers)
    client.post("/v1/housing-units", json={"num_units": 500}, headers=auth_headers)

    response = client.get("/v1/housing-units?num_units_min=10&num_units_max=100")
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(10 <= item["num_units"] <= 100 for item in items)


@pytest.mark.e2e
def test_unauthenticated_write_is_rejected(client: TestClient) -> None:
    """POST, PUT, DELETE all return 401 without auth header."""
    assert client.post("/v1/housing-units", json={"num_units": 1}).status_code == 401
    assert client.put("/v1/housing-units/1", json={"num_units": 1}).status_code == 401
    assert client.delete("/v1/housing-units/1").status_code == 401


@pytest.mark.e2e
def test_get_endpoints_are_public(client: TestClient) -> None:
    """GET endpoints return 200 without auth header."""
    assert client.get("/v1/housing-units").status_code == 200
    assert client.get("/v1/housing-units/999999999").status_code == 404


@pytest.mark.e2e
def test_pagination(client: TestClient, auth_headers: dict) -> None:
    """limit and offset return non-overlapping pages."""
    for i in range(6):
        client.post("/v1/housing-units", json={"num_units": i + 1}, headers=auth_headers)

    page1 = client.get("/v1/housing-units?limit=3&offset=0").json()["items"]
    page2 = client.get("/v1/housing-units?limit=3&offset=3").json()["items"]

    ids1 = {item["id"] for item in page1}
    ids2 = {item["id"] for item in page2}
    assert ids1.isdisjoint(ids2)


@pytest.mark.e2e
def test_geo_rectangle_filter(client: TestClient, auth_headers: dict) -> None:
    """rectangle geo filter returns only rows within the bounding box."""
    client.post(
        "/v1/housing-units",
        json={"num_units": 10, "latitude": 40.70, "longitude": -73.90},
        headers=auth_headers,
    )
    client.post(
        "/v1/housing-units",
        json={"num_units": 10, "latitude": 41.50, "longitude": -75.00},
        headers=auth_headers,
    )

    response = client.get(
        "/v1/housing-units"
        "?geo_shape=rectangle"
        "&min_lat=40.60&max_lat=40.80"
        "&min_lon=-74.00&max_lon=-73.80"
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(
        40.60 <= float(item["latitude"]) <= 40.80
        and -74.00 <= float(item["longitude"]) <= -73.80
        for item in items
        if item["latitude"] is not None
    )
