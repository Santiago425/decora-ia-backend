"""replace the house exterior photo used by the japandi style and the demo bedroom

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-20 19:00:00.000000
"""
import json
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEED_DATA = Path(__file__).resolve().parents[2] / "app" / "seed_data"
EXTERIOR_PHOTO = "https://images.unsplash.com/photo-1600585154340-be6161a56a0c"
STYLE_SLUG = "japandi"
DEMO_PROJECT = "Dormitorio sereno"


def _seed(name: str):
    return json.loads((SEED_DATA / name).read_text(encoding="utf-8"))


def _style_photo() -> str:
    return next(s["image_url"] for s in _seed("catalog.json")["styles"] if s["slug"] == STYLE_SLUG)


def _demo_photo() -> str:
    return next(p["after_image_url"] for p in _seed("demo_projects.json") if p["name"] == DEMO_PROJECT)


def _replace(table: str, column: str, old_prefix: str, new_url: str) -> None:
    target = sa.table(table, sa.column(column, sa.String))
    op.execute(target.update().where(target.c[column].startswith(old_prefix)).values({column: new_url}))


def upgrade() -> None:
    # Only rows still pointing at the exterior photo change; photos uploaded by users are untouched.
    _replace("design_styles", "image_url", EXTERIOR_PHOTO, _style_photo())
    _replace("redesigns", "result_image_url", EXTERIOR_PHOTO, _demo_photo())


def downgrade() -> None:
    """The exterior photo was a seed mistake, so there is nothing to restore."""
