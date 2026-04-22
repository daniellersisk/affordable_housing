# integration test fixtures.
# apply_migrations runs once; db_session wraps each test in a transaction.
# we flush inside tests (not commit) so rollback in the finally block undoes
# everything — keeps the schema clean between tests without truncating tables.
from __future__ import annotations

from collections.abc import Generator

import pytest
from alembic.config import Config
from sqlalchemy.orm import Session

from alembic import command
from app.db.session import SessionLocal


@pytest.fixture(scope="session", autouse=True)
def apply_migrations() -> None:
    """Apply all Alembic migrations before the integration test session starts."""
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


@pytest.fixture
def db_session(apply_migrations: None) -> Generator[Session, None, None]:
    """Yield a session that is always rolled back after each test.

    Flush is used in tests rather than commit, so rollback undoes all changes
    and leaves the schema clean for the next test.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
