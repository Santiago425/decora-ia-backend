from fastapi import APIRouter

from app.core.settings import get_settings
from app.dependencies import CurrentUser
from app.schemas.meta import AppInfo, PublicMeta
from app.services import meta_service

router = APIRouter(prefix="/meta", tags=["Meta"])


@router.get("/public", response_model=PublicMeta)
def public_meta() -> PublicMeta:
    """Brand, active AI providers and demo accounts (when enabled) for the login and documentation screens."""
    return meta_service.public_meta(get_settings())


@router.get("/info", response_model=AppInfo)
def app_info(_user: CurrentUser) -> AppInfo:
    return meta_service.app_info(get_settings())
