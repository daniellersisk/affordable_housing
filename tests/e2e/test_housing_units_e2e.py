"""E2E tests for the housing units API.

Tests call the API over real HTTP (httpx) — no direct service or repository
calls.

Keep E2E small and high-signal. Broad API behavior is covered by contract and
integration tests; E2E exists to prove the running service works over HTTP.
"""
from __future__ import annotations

import pytest


@pytest.mark.e2e
def test_create_read_update_delete_lifecycle(
    e2e_http, e2e_auth_headers: dict, e2e_created_unit_ids: list[int]
) -> None:
    """Full CRUD lifecycle over HTTP, plus basic auth boundary checks."""
    # auth failure (write endpoints)
    assert e2e_http.post("/v1/housing-units", json={"num_units": 1}).status_code == 401

    # public reads
    assert e2e_http.get("/v1/housing-units").status_code == 200

    # create
    created = e2e_http.post(
        "/v1/housing-units",
        json={"num_units": 20, "street_name": "Lifecycle Ave", "borough": "QUEENS"},
        headers=e2e_auth_headers,
    )
    assert created.status_code == 201
    unit = created.json()
    unit_id = unit["id"]
    e2e_created_unit_ids.append(unit_id)
    assert unit["street_name"] == "Lifecycle Ave"

    # read back
    fetched = e2e_http.get(f"/v1/housing-units/{unit_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == unit_id

    # update
    updated = e2e_http.put(
        f"/v1/housing-units/{unit_id}",
        json={"street_name": "Updated Ave", "num_units": 99},
        headers=e2e_auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["street_name"] == "Updated Ave"
    assert updated.json()["num_units"] == 99

    # delete
    deleted = e2e_http.delete(
        f"/v1/housing-units/{unit_id}", headers=e2e_auth_headers
    )
    assert deleted.status_code == 204

    # confirm gone
    gone = e2e_http.get(f"/v1/housing-units/{unit_id}")
    assert gone.status_code == 404
