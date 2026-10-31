import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AssistantRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    page: str = Field(default="dashboard", max_length=20)
    project_id: uuid.UUID | None = None


class ActionResponse(BaseModel):
    type: str
    params: dict


class ChatMessageResponse(BaseModel):
    id: int
    sender: Literal["user", "assistant"]
    content: str
    intent: str | None
    actions: list[ActionResponse]
    created_at: datetime


class AssistantReply(BaseModel):
    message: ChatMessageResponse
    reply: ChatMessageResponse
    provider: str
