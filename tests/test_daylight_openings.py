import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient

from app.models import Base
from tests.test_projects_api import designer, project  # noqa: F401

MIGRATION = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "0012_daylight_and_wall_openings.py"


def load_migration():
    spec = importlib.util.spec_from_file_location("daylight_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_daylight_presets_cover_morning_afternoon_and_night(client: TestClient):
    presets = client.get("/api/v1/catalog/daylight").json()
    assert [preset["slug"] for preset in presets] == ["morning", "afternoon", "night"]
    night = presets[-1]
    assert night["lamp_intensity"] > presets[0]["lamp_intensity"]
    assert night["sun_intensity"] < presets[0]["sun_intensity"]
    assert "prompt" not in night


def test_doors_and_windows_fit_every_room(client: TestClient):
    rooms = {room["slug"] for room in client.get("/api/v1/catalog/room-types").json()}
    categories = {c["slug"]: c for c in client.get("/api/v1/catalog/furniture-categories").json()}
    for slug in ("door", "window"):
        assert categories[slug]["shape"] == slug
        assert rooms <= set(categories[slug]["room_types"])
        assert client.get("/api/v1/catalog/furniture", params={"category": slug}).json()


def test_scene_keeps_the_time_of_day(client: TestClient, designer: dict, project: dict):  # noqa: F811
    scene = project["scene"]
    scene["lighting"]["time_of_day"] = "night"
    url = f"/api/v1/projects/{project['id']}/scene"
    saved = client.put(url, json={"scene": scene}, headers=designer).json()
    assert saved["scene"]["lighting"]["time_of_day"] == "night"


def test_migration_adds_presets_and_openings_to_a_seeded_database(tmp_path: Path):
    migration = load_migration()
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'migration.db'}")
    Base.metadata.create_all(engine)
    Base.metadata.tables["daylight_presets"].drop(engine)
    with engine.begin() as connection:
        connection.execute(
            migration.categories.insert().values(
                slug="sofa", name="Sofás", icon="sofa", shape="sofa", room_types=["living_room"]
            )
        )

    def run(step):
        with engine.begin() as connection, Operations.context(MigrationContext.configure(connection)):
            step()

    def count(table: str) -> int:
        with engine.connect() as connection:
            return connection.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar()

    run(migration.upgrade)
    assert count("daylight_presets") == 3
    assert count("furniture_categories") == 3
    assert count("furniture_items") == 6

    run(migration.downgrade)
    assert count("furniture_categories") == 1
    assert count("furniture_items") == 0
    assert "daylight_presets" not in sa.inspect(engine).get_table_names()
