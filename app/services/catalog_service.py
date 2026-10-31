from app.repositories import (
    FurnitureCategoryRepository,
    FurnitureRepository,
    MaterialRepository,
    PaletteRepository,
    RoomTypeRepository,
    StyleRepository,
)


class CatalogService:
    def __init__(
        self,
        styles: StyleRepository,
        room_types: RoomTypeRepository,
        categories: FurnitureCategoryRepository,
        furniture: FurnitureRepository,
        materials: MaterialRepository,
        palettes: PaletteRepository,
    ) -> None:
        self.styles = styles
        self.room_types = room_types
        self.categories = categories
        self.furniture = furniture
        self.materials = materials
        self.palettes = palettes

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
