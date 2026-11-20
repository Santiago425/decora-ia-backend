"""room specific furniture: bathroom, kitchen and bedroom pieces plus tile and marble finishes

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-20 21:00:00.000000
"""
import json
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEED_DATA = Path(__file__).resolve().parents[2] / "app" / "seed_data"
NEW_CATEGORIES = (
    "toilet",
    "vanity",
    "bathtub",
    "shower",
    "mirror",
    "fridge",
    "stove",
    "counter",
    "nightstand",
    "wardrobe",
    "tv_stand",
)
NEW_MATERIALS = (
    "wall_tile_white_subway",
    "wall_tile_sage",
    "wall_marble_carrara",
    "wall_wood_slats",
    "floor_marble_white",
    "floor_hex_tile_grey",
    "floor_black_slate",
)
NEW_ITEMS_IN_EXISTING_CATEGORIES = ("Butaco alto de cocina",)
WIDER_CATEGORIES = ("chair",)

materials = sa.table(
    "materials",
    sa.column("id", sa.Integer),
    sa.column("slug", sa.String),
    sa.column("name", sa.String),
    sa.column("surface", sa.String),
    sa.column("color_hex", sa.String),
    sa.column("roughness", sa.Float),
    sa.column("metalness", sa.Float),
    sa.column("price_per_unit", sa.Numeric),
    sa.column("texture_url", sa.String),
)
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
    bind = op.get_bind()
    # A fresh database is filled by the seed from the same catalog, so only already seeded databases change here.
    if bind.execute(sa.select(sa.func.count()).select_from(categories)).scalar() == 0:
        return
    catalog = _catalog()

    known_materials = set(bind.execute(sa.select(materials.c.slug)).scalars())
    for material in catalog["materials"]:
        if material["slug"] in NEW_MATERIALS and material["slug"] not in known_materials:
            bind.execute(materials.insert().values({"texture_url": None, **material}))

    known_categories = dict(bind.execute(sa.select(categories.c.slug, categories.c.id)).all())
    for category in catalog["furniture_categories"]:
        if category["slug"] in NEW_CATEGORIES and category["slug"] not in known_categories:
            bind.execute(categories.insert().values(**category))
        elif category["slug"] in WIDER_CATEGORIES:
            bind.execute(
                categories.update()
                .where(categories.c.slug == category["slug"])
                .values(room_types=category["room_types"])
            )

    category_ids = dict(bind.execute(sa.select(categories.c.slug, categories.c.id)).all())
    known_items = set(bind.execute(sa.select(items.c.category_id, items.c.name)).all())
    for item in catalog["furniture_items"]:
        is_new = item["category"] in NEW_CATEGORIES or item["name"] in NEW_ITEMS_IN_EXISTING_CATEGORIES
        if not is_new or (category_ids[item["category"]], item["name"]) in known_items:
            continue
        fields = {key: value for key, value in item.items() if key != "category"}
        bind.execute(items.insert().values(**fields, category_id=category_ids[item["category"]], model_url=None, is_active=True))


def downgrade() -> None:
    bind = op.get_bind()
    new_ids = sa.select(categories.c.id).where(categories.c.slug.in_(NEW_CATEGORIES))
    bind.execute(items.delete().where(items.c.category_id.in_(new_ids)))
    bind.execute(items.delete().where(items.c.name.in_(NEW_ITEMS_IN_EXISTING_CATEGORIES)))
    bind.execute(categories.delete().where(categories.c.slug.in_(NEW_CATEGORIES)))
    bind.execute(materials.delete().where(materials.c.slug.in_(NEW_MATERIALS)))
    chair_rooms = sa.select(categories.c.room_types).where(categories.c.slug == "chair")
    rooms = bind.execute(chair_rooms).scalar()
    if rooms and "kitchen" in rooms:
        bind.execute(
            categories.update()
            .where(categories.c.slug == "chair")
            .values(room_types=[room for room in rooms if room != "kitchen"])
        )
