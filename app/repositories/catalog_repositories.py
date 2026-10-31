from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import ColorPalette, DesignStyle, FurnitureCategory, FurnitureItem, Material, RoomType
from app.repositories.base_repository import BaseRepository


class StyleRepository(BaseRepository[DesignStyle]):
    model = DesignStyle

    def list_active(self) -> list[DesignStyle]:
        query = (
            select(DesignStyle)
            .where(DesignStyle.is_active.is_(True))
            .options(selectinload(DesignStyle.palettes), selectinload(DesignStyle.materials))
            .order_by(DesignStyle.sort_order, DesignStyle.name)
        )
        return list(self.session.scalars(query))

    def get_by_slug(self, slug: str) -> DesignStyle | None:
        return self.session.scalar(select(DesignStyle).where(DesignStyle.slug == slug))


class RoomTypeRepository(BaseRepository[RoomType]):
    model = RoomType

    def list_active(self) -> list[RoomType]:
        query = select(RoomType).where(RoomType.is_active.is_(True)).order_by(RoomType.sort_order, RoomType.name)
        return list(self.session.scalars(query))

    def get_by_slug(self, slug: str) -> RoomType | None:
        return self.session.scalar(select(RoomType).where(RoomType.slug == slug))


class FurnitureCategoryRepository(BaseRepository[FurnitureCategory]):
    model = FurnitureCategory

    def list_ordered(self) -> list[FurnitureCategory]:
        return list(self.session.scalars(select(FurnitureCategory).order_by(FurnitureCategory.name)))

    def get_by_slug(self, slug: str) -> FurnitureCategory | None:
        return self.session.scalar(select(FurnitureCategory).where(FurnitureCategory.slug == slug))


class FurnitureRepository(BaseRepository[FurnitureItem]):
    model = FurnitureItem

    def list_active(self, category_slug: str | None = None) -> list[FurnitureItem]:
        query = (
            select(FurnitureItem)
            .join(FurnitureItem.category)
            .where(FurnitureItem.is_active.is_(True))
            .options(selectinload(FurnitureItem.category))
            .order_by(FurnitureCategory.name, FurnitureItem.price)
        )
        if category_slug:
            query = query.where(FurnitureCategory.slug == category_slug)
        return list(self.session.scalars(query))


class MaterialRepository(BaseRepository[Material]):
    model = Material

    def list_by_surface(self, surface: str | None = None) -> list[Material]:
        query = select(Material).order_by(Material.surface, Material.name)
        if surface:
            query = query.where(Material.surface == surface)
        return list(self.session.scalars(query))

    def get_by_slug(self, slug: str) -> Material | None:
        return self.session.scalar(select(Material).where(Material.slug == slug))


class PaletteRepository(BaseRepository[ColorPalette]):
    model = ColorPalette

    def list_ordered(self) -> list[ColorPalette]:
        return list(self.session.scalars(select(ColorPalette).order_by(ColorPalette.name)))
