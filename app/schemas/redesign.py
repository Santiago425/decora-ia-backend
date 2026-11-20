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
    keep_items: str | None
    edit_tool: NamedRef | None
    inspiration_image_url: str | None = None
    inspiration_name: str | None = None
    suggestions: dict
    estimated_total: Decimal
    error_message: str | None
    created_at: datetime


class VariationRequest(BaseModel):
    style: str | None = Field(default=None, min_length=1, max_length=40)
    palette: list[str] | None = Field(default=None, max_length=8)
    budget: float | None = Field(default=None, ge=0, le=10_000_000_000)
    keep_structure: bool | None = None
    keep_items: str | None = Field(default=None, max_length=200)


class EditFieldOption(BaseModel):
    slug: str
    name: str
    color_hex: str | None = None
    texture_url: str | None = None


class EditFieldResponse(BaseModel):
    key: str
    label: str
    kind: str
    placeholder: str
    options: list[EditFieldOption]


class EditToolResponse(BaseModel):
    key: str
    label: str
    description: str
    fields: list[EditFieldResponse]


class EditRequest(BaseModel):
    tool: str = Field(min_length=1, max_length=30)
    values: dict[str, str] = Field(default_factory=dict, max_length=4)
