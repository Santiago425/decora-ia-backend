import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.models import ProjectStatus


class StyleUsage(BaseModel):
    slug: str
    name: str
    count: int


class DashboardStats(BaseModel):
    projects: int
    redesigns: int
    favorite_style: StyleUsage | None
    total_budget: Decimal


class ActivityItem(BaseModel):
    kind: Literal["project", "redesign"]
    title: str
    project_id: uuid.UUID
    happened_at: datetime


class ProjectSummary(BaseModel):
    id: uuid.UUID
    name: str
    status: ProjectStatus
    style_name: str | None
    room_type_name: str | None
    estimated_budget: Decimal
    before_image_url: str | None
    after_image_url: str | None
    redesign_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime


class DashboardResponse(BaseModel):
    stats: DashboardStats
    style_usage: list[StyleUsage]
    recent_activity: list[ActivityItem]
    recent_projects: list[ProjectSummary]
