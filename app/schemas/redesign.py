import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

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


class VariationRequest(BaseModel):
    style: str | None = Field(default=None, min_length=1, max_length=40)
    palette: list[str] | None = Field(default=None, max_length=8)
    budget: float | None = Field(default=None, ge=0, le=10_000_000_000)
    keep_structure: bool | None = None
