import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import TokenService
from app.core.settings import get_settings
from app.models import User, UserRole
from app.patterns.ai.gemini_adapter import GeminiClient
from app.patterns.assistant.interpreters import (
    FallbackInterpreter,
    GeminiIntentInterpreter,
    IntentInterpreter,
    RuleBasedInterpreter,
)
from app.patterns.proxies.catalog_admin_proxy import CatalogAdminProxy, CatalogAdminService
from app.patterns.reports.report_exporters import ReportExporter, report_for
from app.repositories import (
    AdminStatsRepository,
    ChatMessageRepository,
    FurnitureAddonRepository,
    FurnitureCategoryRepository,
    FurnitureRepository,
    MaterialRepository,
    PaletteRepository,
    ProjectRepository,
    RedesignRepository,
    RoomTypeRepository,
    SceneVersionRepository,
    StyleRepository,
    UserRepository,
)
from app.services.admin_service import AdminService
from app.services.assistant_service import AssistantService
from app.services.auth_service import AuthService
from app.services.catalog_service import CatalogService
from app.services.dashboard_service import DashboardService
from app.services.project_service import ProjectService

DbSession = Annotated[Session, Depends(get_db)]
bearer_scheme = HTTPBearer(auto_error=False)


def get_user_repository(db: DbSession) -> UserRepository:
    return UserRepository(db)


def get_auth_service(users: Annotated[UserRepository, Depends(get_user_repository)]) -> AuthService:
    return AuthService(users)


def get_catalog_service(db: DbSession) -> CatalogService:
    return CatalogService(
        StyleRepository(db),
        RoomTypeRepository(db),
        FurnitureCategoryRepository(db),
        FurnitureRepository(db),
        MaterialRepository(db),
        PaletteRepository(db),
        FurnitureAddonRepository(db),
    )


def get_dashboard_service(db: DbSession) -> DashboardService:
    return DashboardService(ProjectRepository(db), RedesignRepository(db))


def get_project_service(db: DbSession) -> ProjectService:
    return ProjectService(
        ProjectRepository(db),
        SceneVersionRepository(db),
        StyleRepository(db),
        RoomTypeRepository(db),
        FurnitureRepository(db),
        MaterialRepository(db),
        FurnitureAddonRepository(db),
        get_settings(),
    )


def get_interpreter() -> IntentInterpreter:
    settings = get_settings()
    rules = RuleBasedInterpreter()
    if settings.ai_text_provider != "gemini" or not settings.gemini_api_key:
        return rules
    client = GeminiClient(settings.gemini_api_key, settings.gemini_api_base_url, settings.ai_timeout_seconds)
    return FallbackInterpreter(GeminiIntentInterpreter(client, settings.gemini_text_model, settings.currency_code), rules)


def get_assistant_service(
    db: DbSession,
    projects: Annotated[ProjectService, Depends(get_project_service)],
    interpreter: Annotated[IntentInterpreter, Depends(get_interpreter)],
) -> AssistantService:
    return AssistantService(
        ChatMessageRepository(db),
        ProjectRepository(db),
        projects,
        StyleRepository(db),
        RoomTypeRepository(db),
        FurnitureCategoryRepository(db),
        FurnitureRepository(db),
        MaterialRepository(db),
        interpreter,
        get_settings(),
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Tu sesión expiró, vuelve a iniciar sesión")
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Inicia sesión para continuar")
    try:
        payload = TokenService.decode(credentials.credentials)
        user = users.get(uuid.UUID(payload["sub"]))
    except (jwt.PyJWTError, ValueError):
        raise unauthorized from None
    if user is None or not user.is_active:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Necesitas permisos de administrador")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def get_admin_service(db: DbSession) -> AdminService:
    return AdminService(
        AdminStatsRepository(db),
        UserRepository(db),
        FurnitureRepository(db),
        StyleRepository(db),
        FurnitureAddonRepository(db),
        get_settings(),
    )


def get_catalog_admin(db: DbSession, user: CurrentUser) -> CatalogAdminProxy:
    real = CatalogAdminService(
        FurnitureRepository(db), FurnitureCategoryRepository(db), StyleRepository(db), FurnitureAddonRepository(db)
    )
    return CatalogAdminProxy(real, user)


def get_report(kind: str, db: DbSession) -> ReportExporter:
    report = report_for(kind, UserRepository(db), ProjectRepository(db))
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ese reporte no existe")
    return report
