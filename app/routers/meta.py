from fastapi import APIRouter

from app.core.settings import get_settings
from app.dependencies import CurrentUser
from app.schemas.admin import ProviderInfo
from app.schemas.meta import AppInfo, DemoAccount

router = APIRouter(prefix="/meta", tags=["Meta"])


@router.get("/info", response_model=AppInfo)
def app_info(user: CurrentUser) -> AppInfo:
    settings = get_settings()
    accounts = []
    if settings.show_demo_accounts:
        accounts = [
            DemoAccount(
                role="user",
                name=settings.demo_user_name,
                email=settings.demo_user_email,
                password=settings.demo_password,
            ),
            DemoAccount(
                role="admin",
                name=settings.demo_admin_name,
                email=settings.demo_admin_email,
                password=settings.demo_password,
            ),
        ]
    return AppInfo(
        app_name=settings.app_name,
        assistant_name=settings.assistant_name,
        environment=settings.app_env,
        api_prefix=settings.api_prefix,
        providers=ProviderInfo(
            text=settings.ai_text_provider, image=settings.ai_image_provider, storage=settings.storage_provider
        ),
        demo_accounts=accounts,
    )
