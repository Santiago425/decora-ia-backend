"""furniture favorites: pieces each user marks in the editor catalog

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-21 11:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "furniture_favorites",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("furniture_item_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["furniture_item_id"], ["furniture_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "furniture_item_id"),
    )


def downgrade() -> None:
    op.drop_table("furniture_favorites")
