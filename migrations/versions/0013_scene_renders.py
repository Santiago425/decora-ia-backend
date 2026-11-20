"""photorealistic pictures made from captures of the 3D editor

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-20 23:30:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scene_renders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("capture_image_url", sa.String(length=500), nullable=False),
        sa.Column("result_image_url", sa.String(length=500), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("time_of_day", sa.String(length=40), nullable=True),
        sa.Column(
            "status",
            sa.Enum("uploading", "processing", "ready", "error", name="redesignstatus", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("error_message", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scene_renders_project_id"), "scene_renders", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_scene_renders_project_id"), table_name="scene_renders")
    op.drop_table("scene_renders")
