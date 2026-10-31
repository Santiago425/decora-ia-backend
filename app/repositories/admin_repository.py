from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ChatMessage, DesignStyle, Project, Redesign, User


class AdminStatsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def totals(self) -> dict[str, int]:
        models = {"users": User, "projects": Project, "redesigns": Redesign, "assistant_messages": ChatMessage}
        return {key: self.session.scalar(select(func.count()).select_from(model)) or 0 for key, model in models.items()}

    def projects_by_status(self) -> dict[str, int]:
        query = select(Project.status, func.count(Project.id)).group_by(Project.status)
        return {status.value: total for status, total in self.session.execute(query)}

    def redesigns_by_status(self) -> dict[str, int]:
        query = select(Redesign.status, func.count(Redesign.id)).group_by(Redesign.status)
        return {status.value: total for status, total in self.session.execute(query)}

    def style_usage(self, limit: int) -> list[tuple[str, str, int]]:
        query = (
            select(DesignStyle.slug, DesignStyle.name, func.count(Project.id))
            .join(Project, Project.style_id == DesignStyle.id)
            .group_by(DesignStyle.slug, DesignStyle.name)
            .order_by(func.count(Project.id).desc(), DesignStyle.name)
            .limit(limit)
        )
        return [(slug, name, total) for slug, name, total in self.session.execute(query)]

    def daily_counts(self, model, since: datetime) -> dict[str, int]:
        day = func.date(model.created_at)
        query = select(day, func.count()).where(model.created_at >= since).group_by(day)
        return {str(date): total for date, total in self.session.execute(query)}

    def new_users_since(self, since: datetime) -> int:
        return self.session.scalar(select(func.count(User.id)).where(User.created_at >= since)) or 0
