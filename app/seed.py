import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.database import Database
from app.core.security import PasswordHasher
from app.core.settings import get_settings
from app.models import (
    ColorPalette,
    DaylightPreset,
    DesignStyle,
    FurnitureAddon,
    FurnitureItem,
    InspirationPhoto,
    Material,
    Project,
    ProjectStatus,
    Redesign,
    RedesignStatus,
    RoomType,
    User,
    UserRole,
)
from app.repositories import (
    DaylightPresetRepository,
    FurnitureAddonRepository,
    FurnitureCategoryRepository,
    InspirationPhotoRepository,
    MaterialRepository,
    ProjectRepository,
    RoomTypeRepository,
    StyleRepository,
    UserRepository,
)

SEED_DIR = Path(__file__).parent / "seed_data"


def seed_catalog(session: Session, data: dict) -> None:
    room_types = RoomTypeRepository(session)
    for item in data["room_types"]:
        room_type = room_types.get_by_slug(item["slug"])
        if room_type is None:
            session.add(RoomType(**item))
        elif not room_type.cover_image_url:
            room_type.cover_image_url = item.get("cover_image_url")

    materials = MaterialRepository(session)
    for item in data["materials"]:
        material = materials.get_by_slug(item["slug"])
        if material is None:
            session.add(Material(**{**item, "price_per_unit": Decimal(str(item["price_per_unit"]))}))
        elif not material.texture_url:
            material.texture_url = item.get("texture_url")
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
    wall_categories = set(data.get("wall_categories", []))
    for item in data["furniture_categories"]:
        category = categories.get_by_slug(item["slug"])
        if category is None:
            session.add(categories.model(**item, blocks_floor=item["slug"] not in wall_categories))
        elif not category.room_types:
            category.room_types = item["room_types"]
    session.flush()

    if not session.query(FurnitureItem).first():
        details = {detail["name"]: detail for detail in data.get("furniture_details", [])}
        for item in data["furniture_items"]:
            category = categories.get_by_slug(item["category"])
            fields = {k: v for k, v in item.items() if k not in ("category", "price")}
            extra = {k: v for k, v in details.get(item["name"], {}).items() if k != "name"}
            price = Decimal(str(item["price"]))
            session.add(FurnitureItem(**fields, **extra, price=price, category_id=category.id))

    addons = FurnitureAddonRepository(session)
    for item in data["furniture_addons"]:
        if not addons.get_by_slug(item["slug"]):
            session.add(FurnitureAddon(**{**item, "price": Decimal(str(item["price"]))}))
    session.flush()

    daylight = DaylightPresetRepository(session)
    for item in data.get("daylight_presets", []):
        if not daylight.get_by_slug(item["slug"]):
            session.add(DaylightPreset(**item))

    if not InspirationPhotoRepository(session).count():
        for order, item in enumerate(data["inspiration_photos"]):
            style = styles.get_by_slug(item["style"]) if item["style"] else None
            room_type = room_types.get_by_slug(item["room_type"]) if item["room_type"] else None
            fields = {k: v for k, v in item.items() if k not in ("style", "room_type")}
            session.add(
                InspirationPhoto(
                    **fields,
                    sort_order=order,
                    style_id=style.id if style else None,
                    room_type_id=room_type.id if room_type else None,
                )
            )


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


def seed_demo_projects(session: Session, projects: list[dict]) -> None:
    owner = UserRepository(session).get_by_email(get_settings().demo_user_email)
    if owner is None or ProjectRepository(session).count_by_user(owner.id):
        return
    styles, room_types = StyleRepository(session), RoomTypeRepository(session)
    now = datetime.now(UTC)
    for item in projects:
        style = styles.get_by_slug(item["style"])
        created_at = now - timedelta(days=item["days_ago"])
        project = Project(
            owner=owner,
            name=item["name"],
            style_id=style.id,
            room_type_id=room_types.get_by_slug(item["room_type"]).id,
            status=ProjectStatus(item["status"]),
            estimated_budget=Decimal(str(item["estimated_budget"])),
            created_at=created_at,
            updated_at=created_at,
        )
        if item["before_image_url"]:
            project.redesigns.append(
                Redesign(
                    style_id=style.id,
                    original_image_url=item["before_image_url"],
                    result_image_url=item["after_image_url"],
                    status=RedesignStatus.READY,
                    created_at=created_at + timedelta(hours=1),
                )
            )
        session.add(project)


def load(name: str):
    return json.loads((SEED_DIR / name).read_text(encoding="utf-8"))


def run_seed() -> None:
    with Database().session() as session:
        seed_catalog(session, load("catalog.json"))
        seed_demo_accounts(session)
        session.flush()
        if get_settings().seed_demo_projects:
            seed_demo_projects(session, load("demo_projects.json"))
        session.commit()


if __name__ == "__main__":
    run_seed()
    print("Seed completed")
