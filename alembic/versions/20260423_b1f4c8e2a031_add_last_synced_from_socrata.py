"""add_last_synced_from_socrata

Revision ID: b1f4c8e2a031
Revises: 39c99893cbde
Create Date: 2026-04-23 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b1f4c8e2a031"
down_revision: Union[str, None] = "39c99893cbde"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "housing_units",
        sa.Column("last_synced_from_socrata", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("housing_units", "last_synced_from_socrata")
