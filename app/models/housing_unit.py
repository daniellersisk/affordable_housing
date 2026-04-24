# SQLAlchemy ORM model for the housing_units table.
# This model is the persistence representation of a housing unit record.
# API request/response shapes live in app/schemas, not here.
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HousingUnit(Base):
    __tablename__ = "housing_units"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "building_id",
            name="uq_housing_units_project_building",
        ),
        CheckConstraint(
            "num_units >= 0",
            name="ck_housing_units_num_units_non_negative",
        ),
        Index("ix_housing_units_street_name", "street_name"),
        Index("ix_housing_units_borough", "borough"),
        Index("ix_housing_units_postcode", "postcode"),
        Index("ix_housing_units_construction_type", "construction_type"),
    )

    # Internal API identity — never expose source identity as the primary key.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Source identity — composite uniqueness enforces idempotent import upserts.
    # Nullable so manually created records are allowed without source IDs.
    project_id: Mapped[str | None] = mapped_column(String, nullable=True)
    building_id: Mapped[str | None] = mapped_column(String, nullable=True)

    # Filterable string fields — indexed individually for single-column queries.
    street_name: Mapped[str | None] = mapped_column(String, nullable=True)
    borough: Mapped[str | None] = mapped_column(String, nullable=True)
    postcode: Mapped[str | None] = mapped_column(String, nullable=True)
    construction_type: Mapped[str | None] = mapped_column(String, nullable=True)

    # num_units is required and non-negative.
    # Mapped from source field total_units at write time.
    num_units: Mapped[int] = mapped_column(Integer, nullable=False)

    # Optional geo coordinates stored as fixed-precision decimals.
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)

    # Audit timestamps — DB sets both on insert; ORM refreshes updated_at on update.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("now()"),
        onupdate=func.now(),
    )

    # Set only when a row is written from Socrata (import or /refresh).
    # NULL means the row was created manually via POST and has never been synced.
    last_synced_from_socrata: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
    )
