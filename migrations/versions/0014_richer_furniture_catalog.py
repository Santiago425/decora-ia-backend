"""richer furniture catalog: color and finish variants, wall pieces, more furniture and add-ons

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-21 10:00:00.000000
"""

import json
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEED_DATA = Path(__file__).resolve().parents[2] / "app" / "seed_data"
NEW_CATEGORIES = (
    "armchair",
    "pouf",
    "side_table",
    "stool",
    "art",
    "curtain",
    "tv",
    "decor",
    "basket",
    "bath_accessory",
    "washer",
)

categories = sa.table(
    "furniture_categories",
    sa.column("id", sa.Integer),
    sa.column("slug", sa.String),
    sa.column("name", sa.String),
    sa.column("icon", sa.String),
    sa.column("shape", sa.String),
    sa.column("room_types", sa.JSON),
    sa.column("blocks_floor", sa.Boolean),
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
    sa.column("materials", sa.String),
    sa.column("color_options", sa.JSON),
    sa.column("finish_options", sa.JSON),
    sa.column("is_active", sa.Boolean),
)
addons = sa.table(
    "furniture_addons",
    sa.column("id", sa.Integer),
    sa.column("slug", sa.String),
    sa.column("name", sa.String),
    sa.column("description", sa.Text),
    sa.column("price", sa.Numeric),
    sa.column("visual", sa.String),
    sa.column("icon", sa.String),
    sa.column("color_hex", sa.String),
    sa.column("categories", sa.JSON),
    sa.column("is_active", sa.Boolean),
)

VARIANT_FIELDS = ("materials", "color_options", "finish_options")
ORIGINAL_ADDONS = (
    "cushions",
    "throw_blanket",
    "stain_guard",
    "glass_top",
    "brass_legs",
    "led_strip",
    "ceramic_pot",
    "smart_bulb",
)


def _catalog() -> dict:
    return json.loads((SEED_DATA / "catalog.json").read_text(encoding="utf-8"))


def _merge(current: list[str] | None, extra: list[str]) -> list[str]:
    merged = list(current or [])
    return merged + [value for value in extra if value not in merged]


def upgrade() -> None:
    op.add_column(
        "furniture_categories", sa.Column("blocks_floor", sa.Boolean(), nullable=False, server_default=sa.true())
    )
    op.add_column("furniture_items", sa.Column("materials", sa.String(length=160), nullable=False, server_default=""))
    for column in ("color_options", "finish_options"):
        op.add_column("furniture_items", sa.Column(column, sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column(
        "furniture_addons", sa.Column("icon", sa.String(length=40), nullable=False, server_default="sparkles")
    )

    bind = op.get_bind()
    # A fresh database is filled by the seed from the same catalog, so only already seeded databases change here.
    if bind.execute(sa.select(sa.func.count()).select_from(categories)).scalar() == 0:
        return
    catalog = _catalog()

    known_categories = {
        slug: rooms for slug, rooms in bind.execute(sa.select(categories.c.slug, categories.c.room_types))
    }
    wall_categories = set(catalog["wall_categories"])
    for category in catalog["furniture_categories"]:
        slug = category["slug"]
        blocks_floor = slug not in wall_categories
        if slug not in known_categories:
            bind.execute(categories.insert().values(**category, blocks_floor=blocks_floor))
            continue
        bind.execute(
            categories.update()
            .where(categories.c.slug == slug)
            .values(blocks_floor=blocks_floor, room_types=_merge(known_categories[slug], category["room_types"]))
        )

    category_ids = dict(bind.execute(sa.select(categories.c.slug, categories.c.id)).all())
    known_items = {
        (category_id, name): item_id
        for item_id, category_id, name in bind.execute(sa.select(items.c.id, items.c.category_id, items.c.name))
    }
    details = {detail["name"]: detail for detail in catalog["furniture_details"]}
    for item in catalog["furniture_items"]:
        key = (category_ids[item["category"]], item["name"])
        variants = {field: details[item["name"]][field] for field in VARIANT_FIELDS}
        if key in known_items:
            bind.execute(items.update().where(items.c.id == known_items[key]).values(**variants))
            continue
        fields = {field: value for field, value in item.items() if field != "category"}
        bind.execute(items.insert().values(**fields, **variants, category_id=key[0], model_url=None, is_active=True))

    known_addons = {slug: cats for slug, cats in bind.execute(sa.select(addons.c.slug, addons.c.categories))}
    for addon in catalog["furniture_addons"]:
        if addon["slug"] in known_addons:
            bind.execute(
                addons.update()
                .where(addons.c.slug == addon["slug"])
                .values(icon=addon["icon"], categories=_merge(known_addons[addon["slug"]], addon["categories"]))
            )
        else:
            bind.execute(addons.insert().values(**addon, is_active=True))


def downgrade() -> None:
    # New pieces added to the older categories stay, since nothing tells them apart from the admin's own.
    bind = op.get_bind()
    bind.execute(addons.delete().where(addons.c.slug.not_in(ORIGINAL_ADDONS)))
    new_ids = sa.select(categories.c.id).where(categories.c.slug.in_(NEW_CATEGORIES))
    bind.execute(items.delete().where(items.c.category_id.in_(new_ids)))
    bind.execute(categories.delete().where(categories.c.slug.in_(NEW_CATEGORIES)))
    op.drop_column("furniture_addons", "icon")
    op.drop_column("furniture_items", "finish_options")
    op.drop_column("furniture_items", "color_options")
    op.drop_column("furniture_items", "materials")
    op.drop_column("furniture_categories", "blocks_floor")
