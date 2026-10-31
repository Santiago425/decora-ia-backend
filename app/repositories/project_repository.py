import uuid

from sqlalchemy import select

from app.models import Project
from app.repositories.base_repository import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    model = Project

    def list_by_user(self, user_id: uuid.UUID) -> list[Project]:
        query = select(Project).where(Project.user_id == user_id).order_by(Project.updated_at.desc())
        return list(self.session.scalars(query))

    def get_owned(self, project_id: uuid.UUID, user_id: uuid.UUID) -> Project | None:
        return self.session.scalar(select(Project).where(Project.id == project_id, Project.user_id == user_id))
