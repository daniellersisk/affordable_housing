# Database engine and session factory.
# get_db is the FastAPI dependency injected into route handlers that need a session.
# Use Depends(get_db) in routes — never instantiate SessionLocal directly in handlers.
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.settings import settings

engine = create_engine(settings.database_url)

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine, autocommit=False, autoflush=False
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session and guarantees cleanup."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
