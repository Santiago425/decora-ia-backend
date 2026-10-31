import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from app.models import ProjectStatus
from app.schemas.redesign import NamedRef

HexColor = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]
Slug = Annotated[str, Field(min_length=1, max_length=40)]
Coordinate = Annotated[float, Field(ge=-50, le=50)]
Dimension = Annotated[float, Field(gt=0, le=10)]


class SceneRoom(BaseModel):
    width: float = Field(ge=1.5, le=20)
    length: float = Field(ge=1.5, le=20)
    height: float = Field(ge=2, le=5)
    wall_material: Slug | None = None
    floor_material: Slug | None = None


class SceneLighting(BaseModel):
    color: HexColor
    intensity: float = Field(ge=0, le=3)


class SceneItem(BaseModel):
    kind: Literal["item"]
    id: str = Field(min_length=1, max_length=40)
    furniture_id: int | None = None
    name: str = Field(min_length=1, max_length=80)
    category: Slug
    shape: Slug
    position: tuple[Coordinate, Coordinate]
    rotation: float = Field(ge=-360, le=360)
    size: tuple[Dimension, Dimension, Dimension]
    color: HexColor
    price: float = Field(ge=0)
    finish: Slug | None = None
    addons: list[Slug] = Field(default_factory=list, max_length=10)


class SceneGroup(BaseModel):
    kind: Literal["group"]
    id: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=80)
    children: list[Annotated[Union[SceneItem, "SceneGroup"], Field(discriminator="kind")]]  # noqa: UP007 = Field(default_factory=list)


class SceneData(BaseModel):
    format: int = 1
    style: Slug | None = None
    room: SceneRoom
    lighting: SceneLighting
    nodes: list[Annotated[SceneItem | SceneGroup, Field(discriminator="kind")]] = Field(default_factory=list)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    room_type: Slug
    style: Slug
    furnished: bool = True


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    room_type: Slug | None = None
    style: Slug | None = None


class SceneUpdate(BaseModel):
    scene: SceneData


class StatusChange(BaseModel):
    action: Literal["start", "finish", "reopen"]


class VersionCreate(BaseModel):
    label: str = Field(min_length=1, max_length=80)


class ProjectDetail(BaseModel):
    id: uuid.UUID
    name: str
    status: ProjectStatus
    actions: list[str]
    style: NamedRef | None
    room_type: NamedRef | None
    estimated_budget: Decimal
    scene: dict
    cover_image_url: str | None
    created_at: datetime
    updated_at: datetime


class VersionSummary(BaseModel):
    id: int
    label: str
    estimated_budget: Decimal
    items: int
    created_at: datetime


class VersionDetail(VersionSummary):
    scene: dict
