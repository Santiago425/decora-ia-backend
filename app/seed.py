import json
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.database import Database
from app.core.security import PasswordHasher
from app.core.settings import get_settings
from app.models import ColorPalette, DesignStyle, FurnitureItem, Material, RoomType, User, UserRole
from app.repositories import (
    FurnitureCategoryRepository,
    MaterialRepository,
    RoomTypeRepository,
    StyleRepository,
    UserRepository,
)

CATALOG_FILE = Path(__file__).parent / "seed_data" / "catalog.json"


def seed_catalog(session: Session, data: dict) -> None:
    room_types = RoomTypeRepository(session)
    for item in data["room_types"]:
        if not room_types.get_by_slug(item["slug"]):
            session.add(RoomType(**item))

    materials = MaterialRepository(session)
    for item in data["materials"]:
        if not materials.get_by_slug(item["slug"]):
            session.add(Material(**{**item, "price_per_unit": Decimal(str(item["price_per_unit"]))}))
    session.flush()

    styles = StyleRepository(session)
    for item in data["styles"]:
        if styles.get_by_slug(item["slug"]):
            continue
        fields = {k: v for k, v in item.items() if k not in ("materials", "palettes")}
        style = DesignStyle(**fields)
        style.materials = [materials.get_by_slug(slug) for slug in item["materials"]]
        style.palettes = [ColorPalette(**palette) for palette in item["palettes"]]
        session.add(style)

    categories = FurnitureCategoryRepository(session)
    for item in data["furniture_categories"]:
        if not categories.get_by_slug(item["slug"]):
            session.add(categories.model(**item))
    session.flush()

    if not session.query(FurnitureItem).first():
        for item in data["furniture_items"]:
            category = categories.get_by_slug(item["category"])
            fields = {k: v for k, v in item.items() if k != "category"}
            session.add(FurnitureItem(**{**fields, "price": Decimal(str(item["price"])), "category_id": category.id}))


def seed_demo_accounts(session: Session) -> None:
    settings = get_settings()
    users = UserRepository(session)
    accounts = [
        (settings.demo_user_email, settings.demo_user_name, UserRole.USER),
        (settings.demo_admin_email, settings.demo_admin_name, UserRole.ADMIN),
    ]
    for email, name, role in accounts:
        user = users.get_by_email(email) or User(email=email.lower(), full_name=name)
        user.role = role
        user.is_active = True
        user.password_hash = PasswordHasher.hash(settings.demo_password)
        session.add(user)


def run_seed() -> None:
    data = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    with Database().session() as session:
        seed_catalog(session, data)
        seed_demo_accounts(session)
        session.commit()


if __name__ == "__main__":
    run_seed()
    print("Seed completed")
