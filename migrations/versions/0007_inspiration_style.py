"""style taken from an inspiration photo

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-20 18:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("redesigns", sa.Column("inspiration_image_url", sa.String(length=500), nullable=True))
    op.add_column("redesigns", sa.Column("inspiration_name", sa.String(length=80), nullable=True))


def downgrade() -> None:
    op.drop_column("redesigns", "inspiration_name")
    op.drop_column("redesigns", "inspiration_image_url")
