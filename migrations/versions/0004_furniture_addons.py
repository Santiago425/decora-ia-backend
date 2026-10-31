"""furniture addons

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-31 06:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "furniture_addons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("visual", sa.String(length=20), nullable=False),
        sa.Column("color_hex", sa.String(length=7), nullable=True),
        sa.Column("categories", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_furniture_addons_slug"), "furniture_addons", ["slug"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_furniture_addons_slug"), table_name="furniture_addons")
    op.drop_table("furniture_addons")
