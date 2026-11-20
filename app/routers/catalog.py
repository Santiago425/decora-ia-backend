from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.dependencies import CurrentUser, get_catalog_service
from app.schemas.catalog import (
    DaylightPresetResponse,
    FurnitureAddonResponse,
    FurnitureCategoryResponse,
    FurnitureItemResponse,
    InspirationPhotoResponse,
    MaterialResponse,
    PaletteResponse,
    RoomTypeResponse,
    StyleResponse,
)
from app.services.catalog_service import CatalogService, FurnitureNotFound

router = APIRouter(prefix="/catalog", tags=["Catalog"])
Service = Annotated[CatalogService, Depends(get_catalog_service)]


@router.get("/styles", response_model=list[StyleResponse])
def list_styles(service: Service):
    return service.list_styles()


@router.get("/room-types", response_model=list[RoomTypeResponse])
def list_room_types(service: Service):
    return service.list_room_types()


@router.get("/furniture-categories", response_model=list[FurnitureCategoryResponse])
def list_furniture_categories(service: Service):
    return service.list_categories()


@router.get("/furniture", response_model=list[FurnitureItemResponse])
def list_furniture(service: Service, category: Annotated[str | None, Query(max_length=40)] = None):
    return service.list_furniture(category)


@router.get("/materials", response_model=list[MaterialResponse])
def list_materials(service: Service, surface: Annotated[str | None, Query(max_length=20)] = None):
    return service.list_materials(surface)


@router.get("/palettes", response_model=list[PaletteResponse])
def list_palettes(service: Service):
    return service.list_palettes()


@router.get("/addons", response_model=list[FurnitureAddonResponse])
def list_addons(service: Service):
    return service.list_addons()


@router.get("/inspiration", response_model=list[InspirationPhotoResponse])
def list_inspiration(service: Service):
    return service.list_inspiration()


@router.get("/daylight", response_model=list[DaylightPresetResponse])
def list_daylight(service: Service):
    return service.list_daylight()


@router.get("/favorites", response_model=list[int])
def list_favorites(user: CurrentUser, service: Service):
    return service.list_favorites(user.id)


def _set_favorite(service: CatalogService, user_id, item_id: int, favorite: bool) -> Response:
    try:
        service.set_favorite(user_id, item_id, favorite)
    except FurnitureNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ese mueble ya no está en el catálogo") from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/favorites/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_favorite(item_id: int, user: CurrentUser, service: Service):
    return _set_favorite(service, user.id, item_id, True)


@router.delete("/favorites/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(item_id: int, user: CurrentUser, service: Service):
    return _set_favorite(service, user.id, item_id, False)
