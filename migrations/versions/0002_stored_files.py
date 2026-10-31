"""stored files

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-31 05:11:09.061544
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("stored_files",
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("content_type", sa.String(length=60), nullable=False),
    sa.Column("size_bytes", sa.Integer(), nullable=False),
    sa.Column("data", sa.LargeBinary(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint("id")
    )


def downgrade() -> None:
    op.drop_table("stored_files")
