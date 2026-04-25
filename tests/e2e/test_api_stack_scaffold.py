from __future__ import annotations

import pytest


@pytest.mark.e2e
def test_api_health_e2e(e2e_http) -> None:
    """Health endpoint is reachable over HTTP."""
    resp = e2e_http.get("/health")
    assert resp.status_code == 200
