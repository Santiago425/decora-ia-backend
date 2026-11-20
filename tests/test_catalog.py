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


def test_seed_includes_the_extended_style_collection(client: TestClient):
    styles = {style["slug"]: style for style in client.get("/api/v1/catalog/styles").json()}
    extended = ["mediterranean", "rustic", "tropical", "coastal", "art-deco"]
    extended += ["mid-century", "farmhouse", "vintage", "contemporary", "luxury"]
    for slug in extended:
        assert styles[slug]["image_url"]
        assert styles[slug]["description"]
        assert styles[slug]["palettes"][0]["colors"]
        assert len(styles[slug]["materials"]) == 4


def test_new_style_in_database_appears_without_code_changes(client: TestClient):
    with Database().session() as session:
        session.add(DesignStyle(slug="wabi-sabi", name="Wabi-sabi", description="Belleza imperfecta"))
        session.commit()
    slugs = [style["slug"] for style in client.get("/api/v1/catalog/styles").json()]
    assert "wabi-sabi" in slugs


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


def test_inspiration_gallery_comes_from_the_database(client: TestClient):
    photos = client.get("/api/v1/catalog/inspiration").json()
    assert len(photos) >= 12
    assert all(photo["image_url"].startswith("https://") and photo["author_name"] for photo in photos)
    assert any(photo["style"] and photo["style"]["slug"] for photo in photos)
    assert {photo["room_type"]["slug"] for photo in photos if photo["room_type"]} >= {"kitchen", "bedroom"}


def test_room_types_and_materials_carry_photos(client: TestClient):
    assert all(room["cover_image_url"] for room in client.get("/api/v1/catalog/room-types").json())
    materials = client.get("/api/v1/catalog/materials").json()
    assert any(material["texture_url"] for material in materials)


def test_seed_fills_missing_covers_without_overwriting(client: TestClient):
    from app.models import RoomType

    with Database().session() as session:
        rooms = session.query(RoomType).order_by(RoomType.id).all()
        rooms[0].cover_image_url = None
        rooms[1].cover_image_url = "https://images.example.com/custom.jpg"
        session.commit()
    run_seed()
    with Database().session() as session:
        rooms = session.query(RoomType).order_by(RoomType.id).all()
        assert rooms[0].cover_image_url
        assert rooms[1].cover_image_url == "https://images.example.com/custom.jpg"
