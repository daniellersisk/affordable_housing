# Declarative base for all SQLAlchemy ORM models.
# All models must inherit from Base so Alembic can detect them during autogenerate.
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
