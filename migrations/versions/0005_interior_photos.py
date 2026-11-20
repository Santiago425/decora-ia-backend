"""interior photos: room type covers, material textures and inspiration gallery

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-20 15:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("room_types", sa.Column("cover_image_url", sa.String(length=500), nullable=True))
    op.add_column("materials", sa.Column("texture_url", sa.String(length=500), nullable=True))
    op.create_table(
        "inspiration_photos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=80), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("author_name", sa.String(length=80), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("style_id", sa.Integer(), nullable=True),
        sa.Column("room_type_id", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["style_id"], ["design_styles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["room_type_id"], ["room_types.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("inspiration_photos")
    op.drop_column("materials", "texture_url")
    op.drop_column("room_types", "cover_image_url")
