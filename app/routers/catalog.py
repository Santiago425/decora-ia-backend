from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_catalog_service
from app.schemas.catalog import (
    FurnitureCategoryResponse,
    FurnitureItemResponse,
    MaterialResponse,
    PaletteResponse,
    RoomTypeResponse,
    StyleResponse,
)
from app.services.catalog_service import CatalogService

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
