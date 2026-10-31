import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models import RedesignStatus


class NamedRef(BaseModel):
    slug: str
    name: str


class RedesignResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    project_name: str
    status: RedesignStatus
    style: NamedRef | None
    room_type: NamedRef | None
    original_image_url: str
    result_image_url: str | None
    palette: list[str]
    budget: Decimal | None
    budget_tier: str
    keep_structure: bool
    suggestions: dict
    estimated_total: Decimal
    error_message: str | None
    created_at: datetime
