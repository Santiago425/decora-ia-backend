"""furniture category room types

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-31 05:19:10.672984
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("furniture_categories", schema=None) as batch_op:
        batch_op.add_column(sa.Column("room_types", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    with op.batch_alter_table("furniture_categories", schema=None) as batch_op:
        batch_op.drop_column("room_types")
