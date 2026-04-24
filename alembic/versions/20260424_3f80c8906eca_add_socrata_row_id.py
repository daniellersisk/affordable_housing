"""add_socrata_row_id

Revision ID: 3f80c8906eca
Revises: b1f4c8e2a031
Create Date: 2026-04-24 19:09:16.845684

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '3f80c8906eca'
down_revision: Union[str, None] = 'b1f4c8e2a031'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "housing_units",
        sa.Column("socrata_row_id", sa.String(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_housing_units_socrata_row_id",
        "housing_units",
        ["socrata_row_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_housing_units_socrata_row_id",
        "housing_units",
        type_="unique",
    )
    op.drop_column("housing_units", "socrata_row_id")
