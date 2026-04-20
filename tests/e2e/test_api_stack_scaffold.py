from __future__ import annotations

import pytest


@pytest.mark.e2e
@pytest.mark.skip(reason="Implement once the containerized HTTP test flow is wired.")
def test_api_health_e2e() -> None:
    """Scaffold for the first end-to-end stack test."""
