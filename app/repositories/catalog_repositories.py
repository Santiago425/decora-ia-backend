from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models import (
    ColorPalette,
    DesignStyle,
    FurnitureAddon,
    FurnitureCategory,
    FurnitureItem,
    InspirationPhoto,
    Material,
    Project,
    RoomType,
)
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

    def all_with_project_counts(self) -> list[tuple[DesignStyle, int]]:
        project_count = (
            select(func.count(Project.id))
            .where(Project.style_id == DesignStyle.id)
            .correlate(DesignStyle)
            .scalar_subquery()
        )
        query = select(DesignStyle, project_count).order_by(DesignStyle.sort_order, DesignStyle.name)
        return [(style, count) for style, count in self.session.execute(query)]

    def count_active(self) -> int:
        return self.session.scalar(select(func.count(DesignStyle.id)).where(DesignStyle.is_active.is_(True))) or 0


class RoomTypeRepository(BaseRepository[RoomType]):
    model = RoomType

    def list_active(self) -> list[RoomType]:
        query = select(RoomType).where(RoomType.is_active.is_(True)).order_by(RoomType.sort_order, RoomType.name)
        return list(self.session.scalars(query))

    def get_by_slug(self, slug: str) -> RoomType | None:
        return self.session.scalar(select(RoomType).where(RoomType.slug == slug))

    def list_all(self) -> list[RoomType]:
        return list(self.session.scalars(select(RoomType).order_by(RoomType.sort_order, RoomType.name)))


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

    def search(
        self,
        text: str | None,
        category_slug: str | None,
        active: bool | None,
        limit: int,
        offset: int,
    ) -> tuple[list[FurnitureItem], int]:
        filters = []
        if text:
            filters.append(func.lower(FurnitureItem.name).like(f"%{text.lower()}%"))
        if category_slug:
            filters.append(FurnitureCategory.slug == category_slug)
        if active is not None:
            filters.append(FurnitureItem.is_active.is_(active))
        base = select(FurnitureItem).join(FurnitureItem.category).where(*filters)
        total = self.session.scalar(select(func.count()).select_from(base.subquery())) or 0
        query = (
            base.options(selectinload(FurnitureItem.category))
            .order_by(FurnitureCategory.name, FurnitureItem.name)
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(query)), total

    def prices_by_id(self, ids: set[int]) -> dict[int, float]:
        if not ids:
            return {}
        query = select(FurnitureItem.id, FurnitureItem.price).where(FurnitureItem.id.in_(ids))
        return {item_id: float(price) for item_id, price in self.session.execute(query)}

    def by_ids(self, ids: set[int]) -> dict[int, FurnitureItem]:
        if not ids:
            return {}
        query = select(FurnitureItem).where(FurnitureItem.id.in_(ids)).options(selectinload(FurnitureItem.category))
        return {item.id: item for item in self.session.scalars(query)}


class MaterialRepository(BaseRepository[Material]):
    model = Material

    def list_by_surface(self, surface: str | None = None) -> list[Material]:
        query = select(Material).order_by(Material.surface, Material.name)
        if surface:
            query = query.where(Material.surface == surface)
        return list(self.session.scalars(query))

    def get_by_slug(self, slug: str) -> Material | None:
        return self.session.scalar(select(Material).where(Material.slug == slug))

    def prices_by_slug(self) -> dict[str, float]:
        return {
            slug: float(price) for slug, price in self.session.execute(select(Material.slug, Material.price_per_unit))
        }


class PaletteRepository(BaseRepository[ColorPalette]):
    model = ColorPalette

    def list_ordered(self) -> list[ColorPalette]:
        return list(self.session.scalars(select(ColorPalette).order_by(ColorPalette.name)))


class FurnitureAddonRepository(BaseRepository[FurnitureAddon]):
    model = FurnitureAddon

    def list_all(self) -> list[FurnitureAddon]:
        return list(self.session.scalars(select(FurnitureAddon).order_by(FurnitureAddon.price)))

    def list_active(self) -> list[FurnitureAddon]:
        query = select(FurnitureAddon).where(FurnitureAddon.is_active.is_(True)).order_by(FurnitureAddon.price)
        return list(self.session.scalars(query))

    def get_by_slug(self, slug: str) -> FurnitureAddon | None:
        return self.session.scalar(select(FurnitureAddon).where(FurnitureAddon.slug == slug))

    def prices_by_slug(self) -> dict[str, float]:
        return {
            slug: float(price)
            for slug, price in self.session.execute(select(FurnitureAddon.slug, FurnitureAddon.price))
        }


class InspirationPhotoRepository(BaseRepository[InspirationPhoto]):
    model = InspirationPhoto

    def list_active(self) -> list[InspirationPhoto]:
        query = (
            select(InspirationPhoto)
            .where(InspirationPhoto.is_active.is_(True))
            .options(selectinload(InspirationPhoto.style), selectinload(InspirationPhoto.room_type))
            .order_by(InspirationPhoto.sort_order, InspirationPhoto.id)
        )
        return list(self.session.scalars(query))
