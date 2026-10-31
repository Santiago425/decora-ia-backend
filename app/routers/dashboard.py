from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import CurrentUser, get_dashboard_service
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
def overview(user: CurrentUser, service: Annotated[DashboardService, Depends(get_dashboard_service)]):
    return service.overview(user)
