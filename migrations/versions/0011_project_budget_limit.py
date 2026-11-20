"""budget limit and purchased items for the shopping list

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-20 22:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("budget_limit", sa.Numeric(precision=14, scale=2), nullable=True))
    op.add_column("projects", sa.Column("purchased_items", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "purchased_items")
    op.drop_column("projects", "budget_limit")
