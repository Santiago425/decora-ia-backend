import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models import DesignStyle, Project, Redesign
from app.repositories.base_repository import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    model = Project

    def list_by_user(self, user_id: uuid.UUID, limit: int | None = None) -> list[Project]:
        query = (
            select(Project)
            .where(Project.user_id == user_id)
            .options(selectinload(Project.style), selectinload(Project.room_type), selectinload(Project.redesigns))
            .order_by(Project.updated_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(query))

    def get_owned(self, project_id: uuid.UUID, user_id: uuid.UUID) -> Project | None:
        return self.session.scalar(select(Project).where(Project.id == project_id, Project.user_id == user_id))

    def count_by_user(self, user_id: uuid.UUID) -> int:
        return self.session.scalar(select(func.count()).where(Project.user_id == user_id)) or 0

    def total_budget_by_user(self, user_id: uuid.UUID) -> Decimal:
        total = self.session.scalar(select(func.sum(Project.estimated_budget)).where(Project.user_id == user_id))
        return total or Decimal(0)

    def style_usage_by_user(self, user_id: uuid.UUID) -> list[tuple[str, str, int]]:
        query = (
            select(DesignStyle.slug, DesignStyle.name, func.count(Project.id))
            .join(Project, Project.style_id == DesignStyle.id)
            .where(Project.user_id == user_id)
            .group_by(DesignStyle.slug, DesignStyle.name)
            .order_by(func.count(Project.id).desc(), DesignStyle.name)
        )
        return [(slug, name, count) for slug, name, count in self.session.execute(query)]


class RedesignRepository(BaseRepository[Redesign]):
    model = Redesign

    def count_by_user(self, user_id: uuid.UUID) -> int:
        query = select(func.count(Redesign.id)).join(Redesign.project).where(Project.user_id == user_id)
        return self.session.scalar(query) or 0

    def recent_by_user(self, user_id: uuid.UUID, limit: int) -> list[Redesign]:
        query = (
            select(Redesign)
            .join(Redesign.project)
            .where(Project.user_id == user_id)
            .options(selectinload(Redesign.project))
            .order_by(Redesign.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(query))
