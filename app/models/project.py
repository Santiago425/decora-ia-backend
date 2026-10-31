import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, utc_now


def _enum(enum_cls: type[enum.Enum]) -> Enum:
    return Enum(enum_cls, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e])


class ProjectStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_DESIGN = "in_design"
    FINISHED = "finished"


class RedesignStatus(str, enum.Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    room_type_id: Mapped[int | None] = mapped_column(ForeignKey("room_types.id", ondelete="SET NULL"))
    style_id: Mapped[int | None] = mapped_column(ForeignKey("design_styles.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[ProjectStatus] = mapped_column(_enum(ProjectStatus), default=ProjectStatus.DRAFT)
    estimated_budget: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    scene: Mapped[dict | None] = mapped_column(JSON)

    owner: Mapped["User"] = relationship(back_populates="projects")  # noqa: F821
    style: Mapped["DesignStyle | None"] = relationship()  # noqa: F821
    room_type: Mapped["RoomType | None"] = relationship()  # noqa: F821
    redesigns: Mapped[list["Redesign"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="Redesign.created_at.desc()"
    )
    scene_versions: Mapped[list["SceneVersion"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Redesign(Base):
    __tablename__ = "redesigns"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    style_id: Mapped[int | None] = mapped_column(ForeignKey("design_styles.id", ondelete="SET NULL"))
    original_image_url: Mapped[str] = mapped_column(String(500))
    result_image_url: Mapped[str | None] = mapped_column(String(500))
    prompt: Mapped[str] = mapped_column(Text, default="")
    palette: Mapped[list[str]] = mapped_column(JSON, default=list)
    budget: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    keep_structure: Mapped[bool] = mapped_column(Boolean, default=True)
    suggestions: Mapped[list[dict]] = mapped_column(JSON, default=list)
    status: Mapped[RedesignStatus] = mapped_column(_enum(RedesignStatus), default=RedesignStatus.UPLOADING)
    error_message: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped[Project] = relationship(back_populates="redesigns")
    style: Mapped["DesignStyle | None"] = relationship()  # noqa: F821


class SceneVersion(Base):
    __tablename__ = "scene_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(80))
    scene: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped[Project] = relationship(back_populates="scene_versions")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    sender: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    intent: Mapped[str | None] = mapped_column(String(40))
    payload: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
