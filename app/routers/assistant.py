from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.rate_limit import limiter
from app.core.settings import get_settings
from app.dependencies import CurrentUser, get_assistant_service
from app.schemas.assistant import AssistantReply, AssistantRequest, ChatMessageResponse
from app.schemas.common import MessageResponse
from app.services.assistant_service import AssistantService

router = APIRouter(prefix="/assistant", tags=["Assistant"])
settings = get_settings()
Service = Annotated[AssistantService, Depends(get_assistant_service)]


@router.get("/messages", response_model=list[ChatMessageResponse])
def history(user: CurrentUser, service: Service):
    return service.history(user)


@router.post("/messages", response_model=AssistantReply)
@limiter.limit(settings.assistant_rate_limit)
def send_message(request: Request, data: AssistantRequest, user: CurrentUser, service: Service):
    return service.send(user, data)


@router.delete("/messages", response_model=MessageResponse)
def clear_history(user: CurrentUser, service: Service):
    service.clear(user)
    return MessageResponse(message="Conversación borrada")
