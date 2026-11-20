import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.dependencies import CurrentUser, get_report_format, get_shopping_list_service
from app.patterns.reports.report_exporters import ReportFormat, ShoppingListReport
from app.schemas.shopping_list import BudgetLimitUpdate, PurchasedUpdate, ShoppingListOut
from app.services.shopping_list_service import ShoppingListService, ShoppingProjectNotFound

router = APIRouter(prefix="/projects", tags=["Shopping list"])
Service = Annotated[ShoppingListService, Depends(get_shopping_list_service)]
IncludeRedesign = Annotated[bool, Query()]


def handle(action):
    try:
        return action()
    except ShoppingProjectNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontramos ese proyecto") from None


@router.get("/{project_id}/shopping-list", response_model=ShoppingListOut)
def get_shopping_list(
    project_id: uuid.UUID, user: CurrentUser, service: Service, include_redesign: IncludeRedesign = False
):
    return handle(lambda: service.get(user, project_id, include_redesign))


@router.put("/{project_id}/shopping-list/budget", response_model=ShoppingListOut)
def set_budget(
    project_id: uuid.UUID,
    data: BudgetLimitUpdate,
    user: CurrentUser,
    service: Service,
    include_redesign: IncludeRedesign = False,
):
    return handle(lambda: service.set_budget(user, project_id, data.amount, include_redesign))


@router.put("/{project_id}/shopping-list/purchased", response_model=ShoppingListOut)
def set_purchased(
    project_id: uuid.UUID,
    data: PurchasedUpdate,
    user: CurrentUser,
    service: Service,
    include_redesign: IncludeRedesign = False,
):
    return handle(lambda: service.set_purchased(user, project_id, data.keys, include_redesign))


@router.get("/{project_id}/shopping-list/export", response_class=Response)
def export_shopping_list(
    project_id: uuid.UUID,
    user: CurrentUser,
    service: Service,
    fmt: Annotated[ReportFormat, Depends(get_report_format)],
    include_redesign: IncludeRedesign = False,
):
    project = handle(lambda: service.owned(user, project_id))
    report = ShoppingListReport(service.build(project, include_redesign), service.settings.currency_code)
    file_name, content = report.export(fmt)
    return Response(
        content,
        media_type=fmt.media_type,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
