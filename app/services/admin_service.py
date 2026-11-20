import uuid
from datetime import UTC, datetime, timedelta

from app.core.settings import Settings
from app.models import Project, Redesign, User, UserRole
from app.repositories import (
    AdminStatsRepository,
    FurnitureAddonRepository,
    FurnitureRepository,
    RoomTypeRepository,
    StyleRepository,
    UserRepository,
)
from app.schemas.admin import (
    AdminFurniture,
    AdminFurniturePage,
    AdminStats,
    AdminStyle,
    AdminUser,
    AdminUserPage,
    AdminUserUpdate,
    DailyPoint,
    StyleCount,
)
from app.services.meta_service import active_providers


def _clean(text: str | None) -> str | None:
    return text.strip() or None if text else None


class AdminError(Exception):
    def __init__(self, user_message: str, status_code: int = 422) -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.status_code = status_code


class AdminService:
    def __init__(
        self,
        stats: AdminStatsRepository,
        users: UserRepository,
        furniture: FurnitureRepository,
        styles: StyleRepository,
        addons: FurnitureAddonRepository,
        room_types: RoomTypeRepository,
        settings: Settings,
    ) -> None:
        self.stats_repo = stats
        self.users = users
        self.furniture = furniture
        self.styles = styles
        self.addons = addons
        self.room_types = room_types
        self.settings = settings

    def stats(self) -> AdminStats:
        days = self.settings.admin_stats_days
        today = datetime.now(UTC).date()
        start = today - timedelta(days=days - 1)
        since = datetime.combine(start, datetime.min.time(), tzinfo=UTC)
        projects = self.stats_repo.daily_counts(Project, since)
        redesigns = self.stats_repo.daily_counts(Redesign, since)
        users = self.stats_repo.daily_counts(User, since)
        daily = []
        for offset in range(days):
            key = str(start + timedelta(days=offset))
            daily.append(
                DailyPoint(
                    day=key, projects=projects.get(key, 0), redesigns=redesigns.get(key, 0), users=users.get(key, 0)
                )
            )
        return AdminStats(
            totals=self.stats_repo.totals(),
            active_users=self.users.count_active(),
            new_users=self.stats_repo.new_users_since(since),
            users_by_role=self.users.count_by_role(),
            projects_by_status=self.stats_repo.projects_by_status(),
            redesigns_by_status=self.stats_repo.redesigns_by_status(),
            top_styles=[StyleCount(slug=s, name=n, count=c) for s, n, c in self.stats_repo.style_usage(limit=6)],
            daily=daily,
            providers=active_providers(self.settings),
            days=days,
        )

    def list_users(
        self, search: str | None, page: int, role: UserRole | None = None, active: bool | None = None
    ) -> AdminUserPage:
        size = self.settings.admin_page_size
        rows, total = self.users.search(_clean(search), size, (page - 1) * size, role=role, active=active)
        items = [AdminUser.model_validate(user).model_copy(update={"project_count": count}) for user, count in rows]
        return AdminUserPage(items=items, total=total, page=page, page_size=size)

    def update_user(self, actor: User, user_id: uuid.UUID, data: AdminUserUpdate) -> AdminUser:
        user = self.users.get(user_id)
        if user is None:
            raise AdminError("No encontramos ese usuario", 404)
        if user.id == actor.id and (data.is_active is False or data.role == UserRole.USER):
            raise AdminError("No puedes quitarte tu propio acceso de administrador")
        losing_admin = (
            user.role == UserRole.ADMIN and user.is_active and (data.role == UserRole.USER or data.is_active is False)
        )
        if losing_admin and self.users.count_admins() <= 1:
            raise AdminError("Debe quedar al menos un administrador activo")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        saved = self.users.save(user)
        return AdminUser.model_validate(saved).model_copy(update={"project_count": len(saved.projects)})

    def list_furniture(
        self, search: str | None, category: str | None, active: bool | None, page: int
    ) -> AdminFurniturePage:
        size = self.settings.admin_page_size
        items, total = self.furniture.search(_clean(search), _clean(category), active, size, (page - 1) * size)
        return AdminFurniturePage(
            items=[AdminFurniture.model_validate(item) for item in items], total=total, page=page, page_size=size
        )

    def list_styles(self) -> list[AdminStyle]:
        return [
            AdminStyle.model_validate(style).model_copy(update={"project_count": count})
            for style, count in self.styles.all_with_project_counts()
        ]

    def list_addons(self):
        return self.addons.list_all()

    def list_room_types(self):
        return self.room_types.list_all()
