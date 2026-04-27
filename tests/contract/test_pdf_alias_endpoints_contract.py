"""Contract tests for skills-challenge (PDF) paths.

The prompt lists endpoints under `/housing-units` (no `/v1` prefix). The API keeps
`/v1/...` as canonical and exposes `/housing-units...` as an alias for reviewer
ergonomics. These tests ensure the alias paths preserve the same contracts,
including negative paths and structured error envelopes.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.contract
def test_alias_get_housing_units_success_contract(client: TestClient) -> None:
    resp = client.get("/housing-units?limit=1&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data


@pytest.mark.negative
@pytest.mark.contract
def test_alias_get_housing_units_geo_params_without_shape_returns_422(client: TestClient) -> None:
    resp = client.get("/housing-units?min_lat=40.6")
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "INVALID_GEO_FILTER"
    assert "message" in detail
    assert "details" in detail


@pytest.mark.negative
@pytest.mark.contract
def test_alias_get_housing_unit_by_id_not_found_contract(client: TestClient) -> None:
    resp = client.get("/housing-units/999999999")
    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert detail["code"] == "NOT_FOUND"
    assert "message" in detail
    assert "details" in detail


@pytest.mark.negative
@pytest.mark.contract
def test_alias_post_housing_unit_auth_error_contract(client: TestClient) -> None:
    resp = client.post("/housing-units", json={"num_units": 10})
    assert resp.status_code == 401
    detail = resp.json()["detail"]
    assert detail["code"] == "UNAUTHORIZED"
    assert "message" in detail
    assert "details" in detail


@pytest.mark.negative
@pytest.mark.contract
def test_alias_post_housing_unit_validation_error_contract(
    client: TestClient, auth_headers: dict
) -> None:
    resp = client.post("/housing-units", json={"num_units": -1}, headers=auth_headers)
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "VALIDATION_ERROR"


@pytest.mark.negative
@pytest.mark.contract
def test_alias_put_housing_unit_auth_error_contract(client: TestClient) -> None:
    resp = client.put("/housing-units/1", json={"street_name": "X"})
    assert resp.status_code == 401
    detail = resp.json()["detail"]
    assert detail["code"] == "UNAUTHORIZED"


@pytest.mark.negative
@pytest.mark.contract
def test_alias_put_housing_unit_not_found_contract(
    client: TestClient, auth_headers: dict
) -> None:
    resp = client.put(
        "/housing-units/999999999",
        json={"street_name": "Ghost St"},
        headers=auth_headers,
    )
    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert detail["code"] == "NOT_FOUND"


@pytest.mark.negative
@pytest.mark.contract
def test_alias_delete_housing_unit_auth_error_contract(client: TestClient) -> None:
    resp = client.delete("/housing-units/1")
    assert resp.status_code == 401
    detail = resp.json()["detail"]
    assert detail["code"] == "UNAUTHORIZED"


@pytest.mark.negative
@pytest.mark.contract
def test_alias_delete_housing_unit_not_found_contract(
    client: TestClient, auth_headers: dict
) -> None:
    resp = client.delete("/housing-units/999999999", headers=auth_headers)
    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert detail["code"] == "NOT_FOUND"


@pytest.mark.negative
@pytest.mark.contract
def test_alias_refresh_auth_error_contract(client: TestClient) -> None:
    resp = client.post("/housing-units/1/refresh")
    assert resp.status_code == 401
    detail = resp.json()["detail"]
    assert detail["code"] == "UNAUTHORIZED"


@pytest.mark.negative
@pytest.mark.contract
def test_alias_refresh_not_found_contract(
    client: TestClient, auth_headers: dict
) -> None:
    resp = client.post("/housing-units/999999999/refresh", headers=auth_headers)
    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert detail["code"] == "NOT_FOUND"


@pytest.mark.negative
@pytest.mark.contract
def test_alias_refresh_returns_422_for_manually_created_unit(
    client: TestClient, auth_headers: dict
) -> None:
    created = client.post(
        "/housing-units",
        json={"num_units": 10, "street_name": "Manual St"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    unit_id = created.json()["id"]

    resp = client.post(f"/housing-units/{unit_id}/refresh", headers=auth_headers)
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "VALIDATION_ERROR"
    assert "message" in detail

