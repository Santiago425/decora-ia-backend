from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.rate_limit import limiter
from app.core.settings import get_settings
from app.dependencies import CurrentUser, get_auth_service
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthError, AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])
settings = get_settings()
Service = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.register_rate_limit)
def register(request: Request, data: RegisterRequest, service: Service) -> TokenResponse:
    try:
        return service.register(data)
    except AuthError as error:
        raise HTTPException(error.status_code, error.message) from None


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.login_rate_limit)
def login(request: Request, data: LoginRequest, service: Service) -> TokenResponse:
    try:
        return service.login(data)
    except AuthError as error:
        raise HTTPException(error.status_code, error.message) from None


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)
