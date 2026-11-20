import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient

from app.models import Base
from app.patterns.builders.room_builder import RoomBuilder, StarterLayoutDirector
from tests.test_project_patterns import furniture
from tests.test_projects_api import auth

MIGRATION = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "0009_room_furniture.py"


def load_migration():
    spec = importlib.util.spec_from_file_location("room_furniture_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def designer(client: TestClient) -> dict:
    import uuid

    email = f"rooms-{uuid.uuid4().hex[:8]}@example.com"
    session = client.post(
        "/api/v1/auth/register", json={"full_name": "Diseñadora", "email": email, "password": "secreta123"}
    )
    return auth(session.json()["access_token"])


def starter_shapes(client: TestClient, designer: dict, room_type: str) -> set[str]:
    body = {"name": "Cuarto de prueba", "room_type": room_type, "style": "nordic"}
    response = client.post("/api/v1/projects", json=body, headers=designer)
    assert response.status_code == 201
    return {node["shape"] for node in response.json()["scene"]["nodes"]}


def test_every_room_type_has_its_own_furniture(client: TestClient):
    categories = client.get("/api/v1/catalog/furniture-categories").json()
    rooms = {room["slug"] for room in client.get("/api/v1/catalog/room-types").json()}
    for room in rooms:
        own = [c["slug"] for c in categories if c["room_types"] == [room]]
        suggested = [c["slug"] for c in categories if room in c["room_types"]]
        assert len(suggested) >= 4, room
        if room in ("bathroom", "kitchen"):
            assert len(own) >= 3, room


def test_bathroom_project_starts_with_bathroom_pieces(client: TestClient, designer: dict):
    shapes = starter_shapes(client, designer, "bathroom")
    assert {"bathtub", "vanity", "toilet"} <= shapes
    assert "sofa" not in shapes and "bed" not in shapes


def test_kitchen_project_starts_with_kitchen_pieces(client: TestClient, designer: dict):
    shapes = starter_shapes(client, designer, "kitchen")
    assert {"counter", "fridge", "stove"} <= shapes


def test_new_wall_and_floor_finishes_are_listed(client: TestClient):
    slugs = {material["slug"] for material in client.get("/api/v1/catalog/materials").json()}
    assert {"wall_tile_white_subway", "wall_marble_carrara", "floor_marble_white", "floor_hex_tile_grey"} <= slugs


def test_director_keeps_fixtures_ahead_of_generic_storage():
    builder = RoomBuilder(3, 2.5, 2.5)
    StarterLayoutDirector(builder).furnish(
        [furniture(1, "cabinet"), furniture(2, "toilet"), furniture(3, "vanity"), furniture(4, "bathtub")]
    )
    placed = [node["shape"] for node in builder.build()["nodes"]]
    assert placed == ["bathtub", "vanity", "toilet"]


def test_migration_adds_room_furniture_to_a_seeded_database(tmp_path: Path):
    migration = load_migration()
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'migration.db'}")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            migration.categories.insert().values(
                slug="chair", name="Sillas", icon="armchair", shape="chair", room_types=["living_room"]
            )
        )

    def run(step):
        with engine.begin() as connection, Operations.context(MigrationContext.configure(connection)):
            step()

    def count(table, column, values):
        with engine.connect() as connection:
            query = sa.select(sa.func.count()).select_from(table).where(column.in_(values))
            return connection.execute(query).scalar()

    run(migration.upgrade)
    run(migration.upgrade)
    assert count(migration.categories, migration.categories.c.slug, migration.NEW_CATEGORIES) == len(
        migration.NEW_CATEGORIES
    )
    assert count(migration.materials, migration.materials.c.slug, migration.NEW_MATERIALS) == len(
        migration.NEW_MATERIALS
    )
    with engine.connect() as connection:
        items = connection.execute(sa.select(sa.func.count()).select_from(migration.items)).scalar()
        chair_rooms = connection.execute(
            sa.select(migration.categories.c.room_types).where(migration.categories.c.slug == "chair")
        ).scalar()
    assert items == 23
    assert "kitchen" in chair_rooms

    run(migration.downgrade)
    assert count(migration.categories, migration.categories.c.slug, migration.NEW_CATEGORIES) == 0
    with engine.connect() as connection:
        assert connection.execute(sa.select(sa.func.count()).select_from(migration.items)).scalar() == 0
