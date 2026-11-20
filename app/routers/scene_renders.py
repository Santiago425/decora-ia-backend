import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.settings import get_settings
from app.dependencies import CurrentUser
from app.patterns.ai.ai_client import AIClient
from app.patterns.ai.ai_provider import AIError
from app.patterns.storage.storage_adapter import create_storage
from app.patterns.validators.image_validators import ImageValidationError
from app.schemas.scene_render import SceneRenderResponse
from app.services.scene_render_service import SceneRenderNotFound, SceneRenderService

router = APIRouter(prefix="/projects", tags=["Scene renders"])
settings = get_settings()


def get_scene_render_service(db: Annotated[Session, Depends(get_db)]) -> SceneRenderService:
    try:
        ai = AIClient()
    except AIError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, error.user_message) from None
    return SceneRenderService(db, create_storage(db), ai)


Service = Annotated[SceneRenderService, Depends(get_scene_render_service)]


@router.post("/{project_id}/renders", response_model=SceneRenderResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.redesign_rate_limit)
def create_render(
    request: Request,
    project_id: uuid.UUID,
    user: CurrentUser,
    service: Service,
    image: Annotated[UploadFile, File()],
):
    max_bytes = int(settings.max_upload_mb * 1024 * 1024)
    capture = image.file.read(max_bytes + 1)
    try:
        return service.render(user, project_id, capture, image.content_type)
    except SceneRenderNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontramos ese proyecto") from None
    except ImageValidationError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from None


@router.get("/{project_id}/renders", response_model=list[SceneRenderResponse])
def list_renders(project_id: uuid.UUID, user: CurrentUser, service: Service):
    try:
        return service.list_for_project(user, project_id)
    except SceneRenderNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontramos ese proyecto") from None
