import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.dependencies import AdminUser, get_admin_service, get_catalog_admin, get_report
from app.patterns.proxies.catalog_admin_proxy import CatalogAdminError, CatalogAdminProxy
from app.patterns.reports.report_exporters import ReportExporter
from app.schemas.admin import (
    AddonUpdate,
    AdminAddon,
    AdminFurniture,
    AdminStats,
    AdminStyle,
    AdminUserPage,
    AdminUserUpdate,
    FurnitureCreate,
    FurnitureUpdate,
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
    page: Annotated[int, Query(ge=1)] = 1,
):
    return service.list_users(search, page)


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
def update_user(user_id: uuid.UUID, data: AdminUserUpdate, admin: AdminUser, service: Service):
    return handle(lambda: service.update_user(admin, user_id, data))


@router.get("/furniture", response_model=list[AdminFurniture])
def list_furniture(admin: AdminUser, service: Service):
    return service.list_furniture()


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


@router.get("/addons", response_model=list[AdminAddon])
def list_addons(admin: AdminUser, service: Service):
    return service.list_addons()


@router.patch("/addons/{addon_id}", response_model=AdminAddon)
def update_addon(addon_id: int, data: AddonUpdate, catalog: Catalog):
    return handle(lambda: catalog.update_addon(addon_id, data))


@router.get("/reports/{kind}", response_class=Response)
def download_report(admin: AdminUser, report: Annotated[ReportExporter, Depends(get_report)]):
    file_name, content = report.export()
    return Response(
        content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
