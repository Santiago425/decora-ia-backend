import uuid

from app.repositories import (
    DaylightPresetRepository,
    FurnitureAddonRepository,
    FurnitureCategoryRepository,
    FurnitureFavoriteRepository,
    FurnitureRepository,
    InspirationPhotoRepository,
    MaterialRepository,
    PaletteRepository,
    RoomTypeRepository,
    StyleRepository,
)


class FurnitureNotFound(Exception):
    pass


class CatalogService:
    def __init__(
        self,
        styles: StyleRepository,
        room_types: RoomTypeRepository,
        categories: FurnitureCategoryRepository,
        furniture: FurnitureRepository,
        materials: MaterialRepository,
        palettes: PaletteRepository,
        addons: FurnitureAddonRepository,
        inspiration: InspirationPhotoRepository,
        daylight: DaylightPresetRepository,
        favorites: FurnitureFavoriteRepository | None = None,
    ) -> None:
        self.styles = styles
        self.room_types = room_types
        self.categories = categories
        self.furniture = furniture
        self.materials = materials
        self.palettes = palettes
        self.addons = addons
        self.inspiration = inspiration
        self.daylight = daylight
        self.favorites = favorites

    def list_styles(self):
        return self.styles.list_active()

    def list_room_types(self):
        return self.room_types.list_active()

    def list_categories(self):
        return self.categories.list_ordered()

    def list_furniture(self, category: str | None = None):
        return self.furniture.list_active(category)

    def list_materials(self, surface: str | None = None):
        return self.materials.list_by_surface(surface)

    def list_palettes(self):
        return self.palettes.list_ordered()

    def list_addons(self):
        return self.addons.list_active()

    def list_inspiration(self):
        return self.inspiration.list_active()

    def list_daylight(self):
        return self.daylight.list_active()

    def list_favorites(self, user_id: uuid.UUID) -> list[int]:
        return self.favorites.item_ids(user_id)

    def set_favorite(self, user_id: uuid.UUID, item_id: int, favorite: bool) -> None:
        item = self.furniture.get(item_id)
        if item is None or not item.is_active:
            raise FurnitureNotFound
        if favorite:
            self.favorites.mark(user_id, item_id)
        else:
            self.favorites.unmark(user_id, item_id)
