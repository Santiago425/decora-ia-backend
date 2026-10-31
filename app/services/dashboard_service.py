from app.models import Project, User
from app.repositories import ProjectRepository, RedesignRepository
from app.schemas.dashboard import (
    ActivityItem,
    DashboardResponse,
    DashboardStats,
    StyleUsage,
)
from app.services.project_service import to_summary

RECENT_PROJECTS = 6
RECENT_ACTIVITY = 6


class DashboardService:
    def __init__(self, projects: ProjectRepository, redesigns: RedesignRepository) -> None:
        self.projects = projects
        self.redesigns = redesigns

    def overview(self, user: User) -> DashboardResponse:
        usage = [StyleUsage(slug=s, name=n, count=c) for s, n, c in self.projects.style_usage_by_user(user.id)]
        recent = self.projects.list_by_user(user.id, RECENT_PROJECTS)
        stats = DashboardStats(
            projects=self.projects.count_by_user(user.id),
            redesigns=self.redesigns.count_by_user(user.id),
            favorite_style=usage[0] if usage else None,
            total_budget=self.projects.total_budget_by_user(user.id),
        )
        return DashboardResponse(
            stats=stats,
            style_usage=usage,
            recent_activity=self._activity(user, recent),
            recent_projects=[to_summary(project) for project in recent],
        )

    def _activity(self, user: User, recent_projects: list[Project]) -> list[ActivityItem]:
        items = [
            ActivityItem(kind="project", title=p.name, project_id=p.id, happened_at=p.created_at)
            for p in recent_projects
        ]
        items += [
            ActivityItem(kind="redesign", title=r.project.name, project_id=r.project_id, happened_at=r.created_at)
            for r in self.redesigns.recent_by_user(user.id, RECENT_ACTIVITY)
        ]
        return sorted(items, key=lambda item: item.happened_at, reverse=True)[:RECENT_ACTIVITY]
