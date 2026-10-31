from sqlalchemy import func, or_, select

from app.models import Project, User, UserRole
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email.lower()))

    def search(self, text: str | None, limit: int, offset: int) -> tuple[list[tuple[User, int]], int]:
        filters = []
        if text:
            pattern = f"%{text.lower()}%"
            filters.append(or_(func.lower(User.full_name).like(pattern), func.lower(User.email).like(pattern)))
        total = self.session.scalar(select(func.count(User.id)).where(*filters)) or 0
        project_count = (
            select(func.count(Project.id)).where(Project.user_id == User.id).correlate(User).scalar_subquery()
        )
        query = (
            select(User, project_count)
            .where(*filters)
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [(user, count) for user, count in self.session.execute(query)], total

    def count_by_role(self) -> dict[str, int]:
        query = select(User.role, func.count(User.id)).group_by(User.role)
        return {role.value: count for role, count in self.session.execute(query)}

    def count_active(self) -> int:
        return self.session.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0

    def count_admins(self) -> int:
        query = select(func.count(User.id)).where(User.role == UserRole.ADMIN, User.is_active.is_(True))
        return self.session.scalar(query) or 0

    def all_with_project_counts(self) -> list[tuple[User, int]]:
        return self.search(None, limit=10_000, offset=0)[0]
