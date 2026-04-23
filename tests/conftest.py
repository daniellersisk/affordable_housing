from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, get_db
from app.main import app
from app.settings import settings


@pytest.fixture
def db_session_for_client() -> Session:
    """Yield a session for overriding the FastAPI get_db dependency in client tests.

    Does NOT rollback automatically — tests that write data should clean up
    or use the integration db_session fixture instead.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db_session_for_client: Session) -> TestClient:
    """TestClient with the real app and a test DB session injected."""
    app.dependency_overrides[get_db] = lambda: db_session_for_client
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Valid write auth headers using the configured WRITE_API_KEY."""
    return {settings.write_api_key_header: settings.write_api_key}
