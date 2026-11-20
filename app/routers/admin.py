import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.dependencies import AdminUser, get_admin_service, get_catalog_admin, get_report, get_report_format
from app.models import UserRole
from app.patterns.proxies.catalog_admin_proxy import CatalogAdminError, CatalogAdminProxy
from app.patterns.reports.report_exporters import ReportExporter, ReportFormat
from app.schemas.admin import (
    AddonUpdate,
    AdminAddon,
    AdminFurniture,
    AdminFurniturePage,
    AdminRoomType,
    AdminStats,
    AdminStyle,
    AdminUserPage,
    AdminUserUpdate,
    FurnitureCreate,
    FurnitureUpdate,
    RoomTypeUpdate,
    StyleUpdate,
)
from app.schemas.admin import AdminUser as AdminUserResponse
from app.services.admin_service import AdminError, AdminService

router = APIRouter(prefix="/admin", tags=["Admin"])
Service = Annotated[AdminService, Depends(get_admin_service)]
Catalog = Annotated[CatalogAdminProxy, Depends(get_catalog_admin)]


def handle(action):
    try:
        return action()
    except (AdminError, CatalogAdminError) as error:
        raise HTTPException(error.status_code, error.user_message) from None


@router.get("/stats", response_model=AdminStats)
def stats(admin: AdminUser, service: Service):
    return service.stats()


@router.get("/users", response_model=AdminUserPage)
def list_users(
    admin: AdminUser,
    service: Service,
    search: Annotated[str | None, Query(max_length=80)] = None,
    role: UserRole | None = None,
    active: bool | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
):
    return service.list_users(search, page, role=role, active=active)


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
def update_user(user_id: uuid.UUID, data: AdminUserUpdate, admin: AdminUser, service: Service):
    return handle(lambda: service.update_user(admin, user_id, data))


@router.get("/furniture", response_model=AdminFurniturePage)
def list_furniture(
    admin: AdminUser,
    service: Service,
    search: Annotated[str | None, Query(max_length=80)] = None,
    category: Annotated[str | None, Query(max_length=60)] = None,
    active: bool | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
):
    return service.list_furniture(search, category, active, page)


@router.post("/furniture", response_model=AdminFurniture, status_code=status.HTTP_201_CREATED)
def create_furniture(data: FurnitureCreate, catalog: Catalog):
    return handle(lambda: catalog.create_furniture(data))


@router.patch("/furniture/{furniture_id}", response_model=AdminFurniture)
def update_furniture(furniture_id: int, data: FurnitureUpdate, catalog: Catalog):
    return handle(lambda: catalog.update_furniture(furniture_id, data))


@router.get("/styles", response_model=list[AdminStyle])
def list_styles(admin: AdminUser, service: Service):
    return service.list_styles()


@router.patch("/styles/{style_id}", response_model=AdminStyle)
def update_style(style_id: int, data: StyleUpdate, catalog: Catalog):
    return handle(lambda: catalog.update_style(style_id, data))


@router.get("/room-types", response_model=list[AdminRoomType])
def list_room_types(admin: AdminUser, service: Service):
    return service.list_room_types()


@router.patch("/room-types/{room_type_id}", response_model=AdminRoomType)
def update_room_type(room_type_id: int, data: RoomTypeUpdate, catalog: Catalog):
    return handle(lambda: catalog.update_room_type(room_type_id, data))


@router.get("/addons", response_model=list[AdminAddon])
def list_addons(admin: AdminUser, service: Service):
    return service.list_addons()


@router.patch("/addons/{addon_id}", response_model=AdminAddon)
def update_addon(addon_id: int, data: AddonUpdate, catalog: Catalog):
    return handle(lambda: catalog.update_addon(addon_id, data))


@router.get("/reports/{kind}", response_class=Response)
def download_report(
    admin: AdminUser,
    report: Annotated[ReportExporter, Depends(get_report)],
    fmt: Annotated[ReportFormat, Depends(get_report_format)],
):
    file_name, content = report.export(fmt)
    return Response(
        content,
        media_type=fmt.media_type,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
