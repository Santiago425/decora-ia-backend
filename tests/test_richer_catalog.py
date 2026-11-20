import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient

from app.models import Base

MIGRATION = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "0014_richer_furniture_catalog.py"
NEW_COLUMNS = {
    "furniture_categories": ["blocks_floor"],
    "furniture_items": ["materials", "color_options", "finish_options"],
    "furniture_addons": ["icon"],
}


def load_migration():
    spec = importlib.util.spec_from_file_location("richer_catalog_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_room_has_a_wide_choice_of_furniture(client: TestClient):
    rooms = [room["slug"] for room in client.get("/api/v1/catalog/room-types").json()]
    furniture = client.get("/api/v1/catalog/furniture").json()
    for room in rooms:
        fitting = [item for item in furniture if room in item["category"]["room_types"]]
        assert len(fitting) >= 40, room
    slugs = {item["category"]["slug"] for item in furniture}
    assert {"armchair", "pouf", "side_table", "stool", "art", "curtain", "tv", "decor", "basket", "washer"} <= slugs


def test_furniture_comes_with_materials_colors_and_finishes(client: TestClient):
    finishes = {m["slug"] for m in client.get("/api/v1/catalog/materials", params={"surface": "furniture"}).json()}
    for item in client.get("/api/v1/catalog/furniture").json():
        assert item["materials"], item["name"]
        colors = item["color_options"]
        assert colors[0]["hex"] == item["default_color"].lower()
        assert len({color["hex"] for color in colors}) == len(colors) >= 2
        assert set(item["finish_options"]) <= finishes


def test_wall_pieces_do_not_block_the_floor(client: TestClient):
    categories = {c["slug"]: c for c in client.get("/api/v1/catalog/furniture-categories").json()}
    assert not any(categories[slug]["blocks_floor"] for slug in ("art", "curtain", "tv", "window"))
    assert categories["sofa"]["blocks_floor"] and categories["door"]["blocks_floor"]


def test_add_ons_cover_decor_and_services_for_the_new_pieces(client: TestClient):
    addons = client.get("/api/v1/catalog/addons").json()
    assert len(addons) >= 20 and all(addon["icon"] for addon in addons)
    covered = {category for addon in addons for category in addon["categories"]}
    assert {"bed", "art", "tv", "curtain", "armchair", "plant"} <= covered
    visuals = {addon["visual"] for addon in addons}
    assert {"books", "vase", "lamp", "headboard", "towels", "none"} <= visuals


def test_migration_enriches_an_already_seeded_database(tmp_path: Path):
    migration = load_migration()
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'migration.db'}")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        for table, columns in NEW_COLUMNS.items():
            for column in columns:
                connection.execute(sa.text(f"ALTER TABLE {table} DROP COLUMN {column}"))
        connection.execute(
            sa.text(
                "INSERT INTO furniture_categories (id, slug, name, icon, shape, room_types)"
                " VALUES (1, 'sofa', 'Sofás', 'sofa', 'sofa', '[\"living_room\"]')"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO furniture_items (category_id, name, description, price, width, depth, height,"
                " default_color, is_active) VALUES (1, 'Sofá Oslo 3 puestos', '', 2890000, 2.1, 0.9, 0.82,"
                " '#d8c8ae', 1)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO furniture_addons (slug, name, description, price, visual, categories, is_active)"
                " VALUES ('cushions', 'Cojines', '', 120000, 'cushions', '[\"sofa\"]', 1)"
            )
        )

    def run(step):
        with engine.begin() as connection, Operations.context(MigrationContext.configure(connection)):
            step()

    def scalar(query: str):
        with engine.connect() as connection:
            return connection.execute(sa.text(query)).scalar()

    run(migration.upgrade)
    assert scalar("SELECT COUNT(*) FROM furniture_categories WHERE slug = 'tv' AND blocks_floor = 0") == 1
    assert "Lino" in scalar("SELECT materials FROM furniture_items WHERE name = 'Sofá Oslo 3 puestos'")
    assert scalar("SELECT COUNT(*) FROM furniture_items") > 100
    assert "armchair" in scalar("SELECT categories FROM furniture_addons WHERE slug = 'cushions'")
    assert scalar("SELECT icon FROM furniture_addons WHERE slug = 'cushions'") != "sparkles"
    assert scalar("SELECT COUNT(*) FROM furniture_addons") > 20

    run(migration.downgrade)
    assert scalar("SELECT COUNT(*) FROM furniture_addons") == len(migration.ORIGINAL_ADDONS)
    assert scalar("SELECT COUNT(*) FROM furniture_categories WHERE slug = 'tv'") == 0
    assert "materials" not in {column["name"] for column in sa.inspect(engine).get_columns("furniture_items")}
