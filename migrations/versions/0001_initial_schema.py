"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-31 04:43:01.612872
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


LEGACY_TABLES = ("remodel_results", "remodel_requests", "rooms", "design_styles", "users")


def drop_legacy_tables() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = inspector.get_table_names()
    if "users" in tables and "role" not in {column["name"] for column in inspector.get_columns("users")}:
        for table in LEGACY_TABLES:
            op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")


def upgrade() -> None:
    drop_legacy_tables()
    op.create_table("design_styles",
    sa.Column("id", sa.Integer(), nullable=False),
    sa.Column("slug", sa.String(length=40), nullable=False),
    sa.Column("name", sa.String(length=60), nullable=False),
    sa.Column("description", sa.Text(), nullable=False),
    sa.Column("image_url", sa.String(length=500), nullable=True),
    sa.Column("lighting_color", sa.String(length=7), nullable=False),
    sa.Column("lighting_intensity", sa.Float(), nullable=False),
    sa.Column("sort_order", sa.Integer(), nullable=False),
    sa.Column("is_active", sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint("id")
    )
    with op.batch_alter_table("design_styles", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_design_styles_slug"), ["slug"], unique=True)

    op.create_table("furniture_categories",
    sa.Column("id", sa.Integer(), nullable=False),
    sa.Column("slug", sa.String(length=40), nullable=False),
    sa.Column("name", sa.String(length=60), nullable=False),
    sa.Column("icon", sa.String(length=40), nullable=False),
    sa.Column("shape", sa.String(length=40), nullable=False),
    sa.PrimaryKeyConstraint("id")
    )
    with op.batch_alter_table("furniture_categories", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_furniture_categories_slug"), ["slug"], unique=True)

    op.create_table("materials",
    sa.Column("id", sa.Integer(), nullable=False),
    sa.Column("slug", sa.String(length=40), nullable=False),
    sa.Column("name", sa.String(length=60), nullable=False),
    sa.Column("surface", sa.String(length=20), nullable=False),
    sa.Column("color_hex", sa.String(length=7), nullable=False),
    sa.Column("roughness", sa.Float(), nullable=False),
    sa.Column("metalness", sa.Float(), nullable=False),
    sa.Column("price_per_unit", sa.Numeric(precision=12, scale=2), nullable=False),
    sa.PrimaryKeyConstraint("id")
    )
    with op.batch_alter_table("materials", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_materials_slug"), ["slug"], unique=True)

    op.create_table("room_types",
    sa.Column("id", sa.Integer(), nullable=False),
    sa.Column("slug", sa.String(length=40), nullable=False),
    sa.Column("name", sa.String(length=60), nullable=False),
    sa.Column("icon", sa.String(length=40), nullable=False),
    sa.Column("sort_order", sa.Integer(), nullable=False),
    sa.Column("is_active", sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint("id")
    )
    with op.batch_alter_table("room_types", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_room_types_slug"), ["slug"], unique=True)

    op.create_table("users",
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("full_name", sa.String(length=120), nullable=False),
    sa.Column("email", sa.String(length=160), nullable=False),
    sa.Column("password_hash", sa.String(length=255), nullable=False),
    sa.Column("role", sa.Enum("user", "admin", name="userrole", native_enum=False, length=20), nullable=False),
    sa.Column("is_active", sa.Boolean(), nullable=False),
    sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint("id")
    )
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_users_email"), ["email"], unique=True)

    op.create_table("chat_messages",
    sa.Column("id", sa.Integer(), nullable=False),
    sa.Column("user_id", sa.Uuid(), nullable=False),
    sa.Column("sender", sa.String(length=20), nullable=False),
    sa.Column("content", sa.Text(), nullable=False),
    sa.Column("intent", sa.String(length=40), nullable=True),
    sa.Column("payload", sa.JSON(), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id")
    )
    with op.batch_alter_table("chat_messages", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_chat_messages_user_id"), ["user_id"], unique=False)

    op.create_table("color_palettes",
    sa.Column("id", sa.Integer(), nullable=False),
    sa.Column("style_id", sa.Integer(), nullable=True),
    sa.Column("name", sa.String(length=60), nullable=False),
    sa.Column("colors", sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(["style_id"], ["design_styles.id"], ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id")
    )
    op.create_table("furniture_items",
    sa.Column("id", sa.Integer(), nullable=False),
    sa.Column("category_id", sa.Integer(), nullable=False),
    sa.Column("name", sa.String(length=80), nullable=False),
    sa.Column("description", sa.Text(), nullable=False),
    sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column("width", sa.Float(), nullable=False),
    sa.Column("depth", sa.Float(), nullable=False),
    sa.Column("height", sa.Float(), nullable=False),
    sa.Column("default_color", sa.String(length=7), nullable=False),
    sa.Column("model_url", sa.String(length=500), nullable=True),
    sa.Column("is_active", sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(["category_id"], ["furniture_categories.id"], ondelete="RESTRICT"),
    sa.PrimaryKeyConstraint("id")
    )
    with op.batch_alter_table("furniture_items", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_furniture_items_category_id"), ["category_id"], unique=False)

    op.create_table("projects",
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("user_id", sa.Uuid(), nullable=False),
    sa.Column("room_type_id", sa.Integer(), nullable=True),
    sa.Column("style_id", sa.Integer(), nullable=True),
    sa.Column("name", sa.String(length=120), nullable=False),
    sa.Column("status", sa.Enum("draft", "in_design", "finished", name="projectstatus", native_enum=False, length=20), nullable=False),
    sa.Column("estimated_budget", sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column("scene", sa.JSON(), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(["room_type_id"], ["room_types.id"], ondelete="SET NULL"),
    sa.ForeignKeyConstraint(["style_id"], ["design_styles.id"], ondelete="SET NULL"),
    sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id")
    )
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_projects_user_id"), ["user_id"], unique=False)

    op.create_table("style_materials",
    sa.Column("style_id", sa.Integer(), nullable=False),
    sa.Column("material_id", sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="CASCADE"),
    sa.ForeignKeyConstraint(["style_id"], ["design_styles.id"], ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("style_id", "material_id")
    )
    op.create_table("redesigns",
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("project_id", sa.Uuid(), nullable=False),
    sa.Column("style_id", sa.Integer(), nullable=True),
    sa.Column("original_image_url", sa.String(length=500), nullable=False),
    sa.Column("result_image_url", sa.String(length=500), nullable=True),
    sa.Column("prompt", sa.Text(), nullable=False),
    sa.Column("palette", sa.JSON(), nullable=False),
    sa.Column("budget", sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column("keep_structure", sa.Boolean(), nullable=False),
    sa.Column("suggestions", sa.JSON(), nullable=False),
    sa.Column("status", sa.Enum("uploading", "processing", "ready", "error", name="redesignstatus", native_enum=False, length=20), nullable=False),
    sa.Column("error_message", sa.String(length=300), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    sa.ForeignKeyConstraint(["style_id"], ["design_styles.id"], ondelete="SET NULL"),
    sa.PrimaryKeyConstraint("id")
    )
    with op.batch_alter_table("redesigns", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_redesigns_project_id"), ["project_id"], unique=False)

    op.create_table("scene_versions",
    sa.Column("id", sa.Integer(), nullable=False),
    sa.Column("project_id", sa.Uuid(), nullable=False),
    sa.Column("label", sa.String(length=80), nullable=False),
    sa.Column("scene", sa.JSON(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id")
    )
    with op.batch_alter_table("scene_versions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_scene_versions_project_id"), ["project_id"], unique=False)



def downgrade() -> None:
    with op.batch_alter_table("scene_versions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_scene_versions_project_id"))

    op.drop_table("scene_versions")
    with op.batch_alter_table("redesigns", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_redesigns_project_id"))

    op.drop_table("redesigns")
    op.drop_table("style_materials")
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_projects_user_id"))

    op.drop_table("projects")
    with op.batch_alter_table("furniture_items", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_furniture_items_category_id"))

    op.drop_table("furniture_items")
    op.drop_table("color_palettes")
    with op.batch_alter_table("chat_messages", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_chat_messages_user_id"))

    op.drop_table("chat_messages")
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_users_email"))

    op.drop_table("users")
    with op.batch_alter_table("room_types", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_room_types_slug"))

    op.drop_table("room_types")
    with op.batch_alter_table("materials", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_materials_slug"))

    op.drop_table("materials")
    with op.batch_alter_table("furniture_categories", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_furniture_categories_slug"))

    op.drop_table("furniture_categories")
    with op.batch_alter_table("design_styles", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_design_styles_slug"))

    op.drop_table("design_styles")
