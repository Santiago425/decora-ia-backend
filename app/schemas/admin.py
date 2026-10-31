import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models import UserRole
from app.schemas.catalog import FurnitureCategoryResponse

HEX_COLOR = r"^#[0-9a-fA-F]{6}$"


class AdminUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
    role: UserRole
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime
    project_count: int = 0


class AdminUserPage(BaseModel):
    items: list[AdminUser]
    total: int
    page: int
    page_size: int


class AdminUserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


class DailyPoint(BaseModel):
    day: date
    projects: int
    redesigns: int
    users: int


class StyleCount(BaseModel):
    slug: str
    name: str
    count: int


class ProviderInfo(BaseModel):
    text: str
    image: str
    storage: str


class AdminStats(BaseModel):
    totals: dict[str, int]
    active_users: int
    new_users: int
    users_by_role: dict[str, int]
    projects_by_status: dict[str, int]
    redesigns_by_status: dict[str, int]
    top_styles: list[StyleCount]
    daily: list[DailyPoint]
    providers: ProviderInfo
    days: int


class AdminFurniture(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    price: Decimal
    width: float
    depth: float
    height: float
    default_color: str
    is_active: bool
    category: FurnitureCategoryResponse


class FurnitureCreate(BaseModel):
    category: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=500)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    width: float = Field(gt=0, le=10)
    depth: float = Field(gt=0, le=10)
    height: float = Field(gt=0, le=5)
    default_color: str = Field(pattern=HEX_COLOR)


class FurnitureUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=1, max_length=40)
    name: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    width: float | None = Field(default=None, gt=0, le=10)
    depth: float | None = Field(default=None, gt=0, le=10)
    height: float | None = Field(default=None, gt=0, le=5)
    default_color: str | None = Field(default=None, pattern=HEX_COLOR)
    is_active: bool | None = None


class AdminStyle(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    description: str
    image_url: str | None
    lighting_color: str
    lighting_intensity: float
    is_active: bool
    project_count: int = 0


class StyleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=60)
    description: str | None = Field(default=None, max_length=500)
    image_url: str | None = Field(default=None, max_length=500)
    lighting_color: str | None = Field(default=None, pattern=HEX_COLOR)
    lighting_intensity: float | None = Field(default=None, ge=0.3, le=2)
    is_active: bool | None = None


class AdminAddon(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    description: str
    price: Decimal
    is_active: bool
    categories: list[str]


class AddonUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    is_active: bool | None = None
