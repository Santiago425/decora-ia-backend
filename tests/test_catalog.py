from fastapi.testclient import TestClient

from app.core.database import Database
from app.models import DesignStyle
from app.seed import run_seed


def test_styles_come_from_the_database_with_palettes_and_materials(client: TestClient):
    styles = client.get("/api/v1/catalog/styles").json()
    slugs = [style["slug"] for style in styles]
    assert {"nordic", "industrial", "japandi"} <= set(slugs)
    nordic = next(style for style in styles if style["slug"] == "nordic")
    assert nordic["palettes"][0]["colors"]
    assert nordic["materials"]


def test_new_style_in_database_appears_without_code_changes(client: TestClient):
    with Database().session() as session:
        session.add(DesignStyle(slug="coastal", name="Costero", description="Azules y arena"))
        session.commit()
    slugs = [style["slug"] for style in client.get("/api/v1/catalog/styles").json()]
    assert "coastal" in slugs


def test_furniture_can_be_filtered_by_category(client: TestClient):
    sofas = client.get("/api/v1/catalog/furniture", params={"category": "sofa"}).json()
    assert sofas
    assert all(item["category"]["slug"] == "sofa" for item in sofas)


def test_other_catalog_endpoints(client: TestClient):
    assert len(client.get("/api/v1/catalog/room-types").json()) >= 4
    assert client.get("/api/v1/catalog/furniture-categories").json()[0]["shape"]
    floors = client.get("/api/v1/catalog/materials", params={"surface": "floor"}).json()
    assert floors and all(material["surface"] == "floor" for material in floors)
    assert client.get("/api/v1/catalog/palettes").json()


def test_seed_is_idempotent(client: TestClient):
    before = len(client.get("/api/v1/catalog/furniture").json())
    run_seed()
    assert len(client.get("/api/v1/catalog/furniture").json()) == before
