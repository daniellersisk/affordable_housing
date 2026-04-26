# Database engine and session factory.
# get_db is the FastAPI dependency injected into route handlers that need a session.
# Use Depends(get_db) in routes — never instantiate SessionLocal directly in handlers.
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.settings import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout_seconds,
    pool_recycle=settings.db_pool_recycle_seconds,
    connect_args={
        "connect_timeout": settings.db_connect_timeout_seconds,
        "options": f"-c statement_timeout={settings.db_statement_timeout_ms}",
    },
)

SessionLocal: sessionmaker[Session] = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session and guarantees cleanup."""
    session = SessionLocal()
    try:
        yield session
        # If the route handler didn't commit, end the transaction cleanly.
        session.rollback()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
