from fastapi import APIRouter
from sqlalchemy import text

from app.core.settings import get_settings
from app.dependencies import DbSession
from app.schemas.common import HealthResponse, MessageResponse

router = APIRouter(tags=["Health"])


@router.get("/hello", response_model=MessageResponse)
def hello() -> MessageResponse:
    return MessageResponse(message=f"Hello World from {get_settings().app_name}")


@router.get("/health", response_model=HealthResponse)
def health(db: DbSession) -> HealthResponse:
    try:
        db.execute(text("SELECT 1"))
        database = "up"
    except Exception:
        database = "down"
    return HealthResponse(status="up", database=database, environment=get_settings().app_env)
