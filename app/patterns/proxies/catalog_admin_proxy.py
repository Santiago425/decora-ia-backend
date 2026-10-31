import logging
from typing import Protocol

from app.models import DesignStyle, FurnitureAddon, FurnitureItem, User, UserRole
from app.repositories import FurnitureAddonRepository, FurnitureCategoryRepository, FurnitureRepository, StyleRepository
from app.schemas.admin import AddonUpdate, FurnitureCreate, FurnitureUpdate, StyleUpdate

logger = logging.getLogger("habita.admin")


class CatalogAdminError(Exception):
    def __init__(self, user_message: str, status_code: int = 422) -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.status_code = status_code


class CatalogAdmin(Protocol):
    def create_furniture(self, data: FurnitureCreate) -> FurnitureItem: ...
    def update_furniture(self, furniture_id: int, data: FurnitureUpdate) -> FurnitureItem: ...
    def update_style(self, style_id: int, data: StyleUpdate) -> DesignStyle: ...
    def update_addon(self, addon_id: int, data: AddonUpdate) -> FurnitureAddon: ...


class CatalogAdminService:
    def __init__(
        self,
        furniture: FurnitureRepository,
        categories: FurnitureCategoryRepository,
        styles: StyleRepository,
        addons: FurnitureAddonRepository,
    ) -> None:
        self.furniture = furniture
        self.categories = categories
        self.styles = styles
        self.addons = addons

    def create_furniture(self, data: FurnitureCreate) -> FurnitureItem:
        values = data.model_dump(exclude={"category"})
        item = FurnitureItem(**values, category_id=self._category_id(data.category))
        return self.furniture.add(item)

    def update_furniture(self, furniture_id: int, data: FurnitureUpdate) -> FurnitureItem:
        item = self.furniture.get(furniture_id)
        if item is None:
            raise CatalogAdminError("No encontramos ese mueble", 404)
        changes = data.model_dump(exclude_unset=True, exclude={"category"})
        if data.category is not None:
            item.category_id = self._category_id(data.category)
        for field, value in changes.items():
            setattr(item, field, value.strip() if isinstance(value, str) else value)
        saved = self.furniture.save(item)
        self.furniture.session.refresh(saved, ["category"])
        return saved

    def update_style(self, style_id: int, data: StyleUpdate) -> DesignStyle:
        style = self.styles.get(style_id)
        if style is None:
            raise CatalogAdminError("No encontramos ese estilo", 404)
        if data.is_active is False and style.is_active and self.styles.count_active() <= 1:
            raise CatalogAdminError("Debe quedar al menos un estilo activo")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(style, field, value)
        return self.styles.save(style)

    def update_addon(self, addon_id: int, data: AddonUpdate) -> FurnitureAddon:
        addon = self.addons.get(addon_id)
        if addon is None:
            raise CatalogAdminError("No encontramos ese complemento", 404)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(addon, field, value)
        return self.addons.save(addon)

    def _category_id(self, slug: str) -> int:
        category = self.categories.get_by_slug(slug)
        if category is None:
            raise CatalogAdminError("Esa categoría no existe")
        return category.id


# Protection Proxy: same interface as the real service, but it checks who is asking and records every change.
class CatalogAdminProxy:
    def __init__(self, real: CatalogAdmin, actor: User) -> None:
        self._real = real
        self._actor = actor

    def create_furniture(self, data: FurnitureCreate) -> FurnitureItem:
        self._authorize()
        item = self._real.create_furniture(data)
        self._audit("create_furniture", item.id)
        return item

    def update_furniture(self, furniture_id: int, data: FurnitureUpdate) -> FurnitureItem:
        self._authorize()
        item = self._real.update_furniture(furniture_id, data)
        self._audit("update_furniture", furniture_id, data.model_dump(exclude_unset=True))
        return item

    def update_style(self, style_id: int, data: StyleUpdate) -> DesignStyle:
        self._authorize()
        style = self._real.update_style(style_id, data)
        self._audit("update_style", style_id, data.model_dump(exclude_unset=True))
        return style

    def update_addon(self, addon_id: int, data: AddonUpdate) -> FurnitureAddon:
        self._authorize()
        addon = self._real.update_addon(addon_id, data)
        self._audit("update_addon", addon_id, data.model_dump(exclude_unset=True))
        return addon

    def _authorize(self) -> None:
        if self._actor.role != UserRole.ADMIN or not self._actor.is_active:
            raise CatalogAdminError("Necesitas permisos de administrador", 403)

    def _audit(self, action: str, target: int, changes: dict | None = None) -> None:
        logger.info("admin=%s action=%s target=%s changes=%s", self._actor.email, action, target, changes or {})
