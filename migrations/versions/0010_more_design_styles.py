"""add the new design styles from the seed catalog to existing databases

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-20 21:00:00.000000
"""
import json
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEED_DATA = Path(__file__).resolve().parents[2] / "app" / "seed_data"
NEW_STYLES = (
    "mediterranean",
    "rustic",
    "tropical",
    "coastal",
    "art-deco",
    "mid-century",
    "farmhouse",
    "vintage",
    "contemporary",
    "luxury",
)

styles = sa.table(
    "design_styles",
    sa.column("id", sa.Integer),
    sa.column("slug", sa.String),
    sa.column("name", sa.String),
    sa.column("description", sa.Text),
    sa.column("image_url", sa.String),
    sa.column("lighting_color", sa.String),
    sa.column("lighting_intensity", sa.Float),
    sa.column("sort_order", sa.Integer),
    sa.column("is_active", sa.Boolean),
)
palettes = sa.table(
    "color_palettes",
    sa.column("style_id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("colors", sa.JSON),
)
materials = sa.table("materials", sa.column("id", sa.Integer), sa.column("slug", sa.String))
style_materials = sa.table("style_materials", sa.column("style_id", sa.Integer), sa.column("material_id", sa.Integer))

STYLE_FIELDS = ("slug", "name", "description", "image_url", "lighting_color", "lighting_intensity", "sort_order")


def _seed_styles() -> list[dict]:
    catalog = json.loads((SEED_DATA / "catalog.json").read_text(encoding="utf-8"))
    return [style for style in catalog["styles"] if style["slug"] in NEW_STYLES]


def upgrade() -> None:
    # Only styles that are not in the database yet are inserted, so databases seeded on startup are left as they are.
    bind = op.get_bind()
    for item in _seed_styles():
        if bind.execute(sa.select(styles.c.id).where(styles.c.slug == item["slug"])).first():
            continue
        bind.execute(styles.insert().values(**{field: item[field] for field in STYLE_FIELDS}, is_active=True))
        style_id = bind.execute(sa.select(styles.c.id).where(styles.c.slug == item["slug"])).scalar_one()
        for palette in item["palettes"]:
            bind.execute(palettes.insert().values(style_id=style_id, name=palette["name"], colors=palette["colors"]))
        material_ids = bind.execute(
            sa.select(materials.c.id).where(materials.c.slug.in_(item["materials"]))
        ).scalars()
        for material_id in material_ids:
            bind.execute(style_materials.insert().values(style_id=style_id, material_id=material_id))


def downgrade() -> None:
    bind = op.get_bind()
    style_ids = bind.execute(sa.select(styles.c.id).where(styles.c.slug.in_(NEW_STYLES))).scalars().all()
    if not style_ids:
        return
    bind.execute(style_materials.delete().where(style_materials.c.style_id.in_(style_ids)))
    bind.execute(palettes.delete().where(palettes.c.style_id.in_(style_ids)))
    bind.execute(styles.delete().where(styles.c.id.in_(style_ids)))
