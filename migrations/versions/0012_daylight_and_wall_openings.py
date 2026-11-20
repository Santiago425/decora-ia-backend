"""daylight presets for the 3D editor plus doors and windows in the furniture catalog

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-20 23:00:00.000000
"""
import json
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEED_DATA = Path(__file__).resolve().parents[2] / "app" / "seed_data"
NEW_CATEGORIES = ("door", "window")

categories = sa.table(
    "furniture_categories",
    sa.column("id", sa.Integer),
    sa.column("slug", sa.String),
    sa.column("name", sa.String),
    sa.column("icon", sa.String),
    sa.column("shape", sa.String),
    sa.column("room_types", sa.JSON),
)
items = sa.table(
    "furniture_items",
    sa.column("id", sa.Integer),
    sa.column("category_id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("description", sa.Text),
    sa.column("price", sa.Numeric),
    sa.column("width", sa.Float),
    sa.column("depth", sa.Float),
    sa.column("height", sa.Float),
    sa.column("default_color", sa.String),
    sa.column("model_url", sa.String),
    sa.column("is_active", sa.Boolean),
)


def _catalog() -> dict:
    return json.loads((SEED_DATA / "catalog.json").read_text(encoding="utf-8"))


def upgrade() -> None:
    presets = op.create_table(
        "daylight_presets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("sun_color", sa.String(length=7), nullable=False),
        sa.Column("sun_intensity", sa.Float(), nullable=False),
        sa.Column("sun_elevation", sa.Float(), nullable=False),
        sa.Column("sun_azimuth", sa.Float(), nullable=False),
        sa.Column("ambient_color", sa.String(length=7), nullable=False),
        sa.Column("ambient_intensity", sa.Float(), nullable=False),
        sa.Column("sky_color", sa.String(length=7), nullable=False),
        sa.Column("window_intensity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("lamp_intensity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("prompt", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_daylight_presets_slug"), "daylight_presets", ["slug"], unique=True)

    bind = op.get_bind()
    catalog = _catalog()
    bind.execute(presets.insert(), [{"is_active": True, **preset} for preset in catalog["daylight_presets"]])

    # A fresh database is filled by the seed from the same catalog, so only already seeded databases change here.
    if bind.execute(sa.select(sa.func.count()).select_from(categories)).scalar() == 0:
        return
    known_categories = set(bind.execute(sa.select(categories.c.slug)).scalars())
    for category in catalog["furniture_categories"]:
        if category["slug"] in NEW_CATEGORIES and category["slug"] not in known_categories:
            bind.execute(categories.insert().values(**category))

    category_ids = dict(bind.execute(sa.select(categories.c.slug, categories.c.id)).all())
    known_items = set(bind.execute(sa.select(items.c.category_id, items.c.name)).all())
    for item in catalog["furniture_items"]:
        if item["category"] not in NEW_CATEGORIES or (category_ids[item["category"]], item["name"]) in known_items:
            continue
        fields = {key: value for key, value in item.items() if key != "category"}
        bind.execute(
            items.insert().values(**fields, category_id=category_ids[item["category"]], model_url=None, is_active=True)
        )


def downgrade() -> None:
    bind = op.get_bind()
    new_ids = sa.select(categories.c.id).where(categories.c.slug.in_(NEW_CATEGORIES))
    bind.execute(items.delete().where(items.c.category_id.in_(new_ids)))
    bind.execute(categories.delete().where(categories.c.slug.in_(NEW_CATEGORIES)))
    op.drop_index(op.f("ix_daylight_presets_slug"), table_name="daylight_presets")
    op.drop_table("daylight_presets")
