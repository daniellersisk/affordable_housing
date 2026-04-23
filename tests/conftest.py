from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import engine, get_db
from app.main import app
from app.settings import settings


@pytest.fixture
def db_session_for_client() -> Session:
    """Yield a session that always rolls back after the test, even if the route commits.

    Uses join_transaction_mode='create_savepoint' so session.commit() in route
    handlers releases a savepoint rather than committing to the DB. The outer
    connection-level transaction is rolled back at teardown, leaving the DB clean.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session_for_client: Session) -> TestClient:
    """TestClient with the real app and a rollback-isolated DB session injected."""
    app.dependency_overrides[get_db] = lambda: db_session_for_client
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Valid write auth headers using the configured WRITE_API_KEY."""
    return {settings.write_api_key_header: settings.write_api_key}
