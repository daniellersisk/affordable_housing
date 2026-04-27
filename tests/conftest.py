from __future__ import annotations

import socket
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import engine, get_db
from app.main import app
from app.settings import settings


@pytest.fixture(autouse=True)
def block_outbound_network(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Fail fast on accidental outbound network calls.

    Allowed destinations:
    - localhost (E2E uvicorn)
    - docker-compose service host `db` (Postgres)

    Any test may opt out with `@pytest.mark.allow_network`.
    """
    if request.node.get_closest_marker("allow_network") is not None:
        yield
        return

    allowed_hosts = {"127.0.0.1", "localhost", "::1", "db"}
    real_create_connection = socket.create_connection

    def guarded_create_connection(address: object, *args: object, **kwargs: object):  # type: ignore[override]
        host: str | None = None
        if isinstance(address, tuple) and len(address) >= 1:
            host = str(address[0])
        if host is not None and host in allowed_hosts:
            return real_create_connection(address, *args, **kwargs)
        raise RuntimeError(
            f"Outbound network blocked in tests (host={host!r}). "
            "Mock HTTP calls (e.g. patch httpx) or mark the test with @pytest.mark.allow_network."
        )

    socket.create_connection = guarded_create_connection  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.create_connection = real_create_connection  # type: ignore[assignment]


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
