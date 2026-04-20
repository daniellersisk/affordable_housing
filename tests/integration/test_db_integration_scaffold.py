from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.skip(reason="Implement once SQLAlchemy session and migrations exist.")
def test_database_session_smoke_integration() -> None:
    """Scaffold for the first real Postgres-backed integration test."""
