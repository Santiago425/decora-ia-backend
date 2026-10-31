import uuid

from app.core.settings import Settings
from app.models import Project, SceneVersion, User
from app.patterns.builders.room_builder import RoomBuilder, StarterLayoutDirector
from app.patterns.mementos.scene_memento import ProjectSceneOriginator
from app.patterns.prototypes.project_prototype import ProjectPrototype
from app.patterns.states.project_states import ProjectLifecycle
from app.patterns.visitors.scene_visitors import (
    BudgetVisitor,
    FurnitureIdCollector,
    walk_scene,
)
from app.repositories import (
    FurnitureAddonRepository,
    FurnitureRepository,
    MaterialRepository,
    ProjectRepository,
    RoomTypeRepository,
    SceneVersionRepository,
    StyleRepository,
)
from app.schemas.dashboard import ProjectSummary
from app.schemas.project import (
    ProjectCreate,
    ProjectDetail,
    ProjectUpdate,
    SceneData,
    VersionDetail,
    VersionSummary,
)
from app.schemas.redesign import NamedRef


class ProjectNotFound(Exception):
    pass


class ProjectInputError(Exception):
    def __init__(self, user_message: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message


def to_summary(project: Project) -> ProjectSummary:
    latest = project.redesigns[0] if project.redesigns else None
    return ProjectSummary(
        id=project.id,
        name=project.name,
        status=project.status,
        style_name=project.style.name if project.style else None,
        room_type_name=project.room_type.name if project.room_type else None,
        estimated_budget=project.estimated_budget,
        before_image_url=latest.original_image_url if latest else None,
        after_image_url=latest.result_image_url if latest else None,
        redesign_count=len(project.redesigns),
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


class ProjectService:
    def __init__(
        self,
        projects: ProjectRepository,
        versions: SceneVersionRepository,
        styles: StyleRepository,
        room_types: RoomTypeRepository,
        furniture: FurnitureRepository,
        materials: MaterialRepository,
        addons: FurnitureAddonRepository,
        settings: Settings,
    ) -> None:
        self.projects = projects
        self.versions = versions
        self.styles = styles
        self.room_types = room_types
        self.furniture = furniture
        self.materials = materials
        self.addons = addons
        self.settings = settings

    @property
    def session(self):
        return self.projects.session

    def list_for(self, user: User) -> list[ProjectSummary]:
        return [to_summary(project) for project in self.projects.list_by_user(user.id)]

    def create(self, user: User, data: ProjectCreate) -> ProjectDetail:
        style, room_type = self._style(data.style), self._room_type(data.room_type)
        project = Project(user_id=user.id, name=data.name.strip(), style_id=style.id, room_type_id=room_type.id)
        project.scene = self._starter_scene(style, room_type, data.furnished)
        project.estimated_budget = self.estimate(project.scene)
        self.projects.add(project)
        return self.get(user, project.id)

    def get(self, user: User, project_id: uuid.UUID) -> ProjectDetail:
        project = self._owned(user, project_id)
        if not project.scene:
            project.scene = self._starter_scene(project.style, project.room_type, furnished=True)
            self.session.commit()
        return self._detail(project)

    def update(self, user: User, project_id: uuid.UUID, data: ProjectUpdate) -> ProjectDetail:
        project = self._owned(user, project_id)
        if data.name is not None:
            project.name = data.name.strip()
        if data.style is not None:
            project.style_id = self._style(data.style).id
        if data.room_type is not None:
            project.room_type_id = self._room_type(data.room_type).id
        self.session.commit()
        return self.get(user, project_id)

    def save_scene(self, user: User, project_id: uuid.UUID, scene: SceneData) -> ProjectDetail:
        project = self._owned(user, project_id)
        ProjectLifecycle(project).edit()
        data = scene.model_dump()
        collector = walk_scene(data, FurnitureIdCollector())
        if collector.count > self.settings.scene_max_nodes:
            raise ProjectInputError(f"La escena admite hasta {self.settings.scene_max_nodes} muebles")
        project.scene = data
        project.estimated_budget = self.estimate(data)
        self.session.commit()
        return self.get(user, project_id)

    def change_status(self, user: User, project_id: uuid.UUID, action: str) -> ProjectDetail:
        project = self._owned(user, project_id)
        ProjectLifecycle(project).apply(action)
        self.session.commit()
        return self.get(user, project_id)

    def duplicate(self, user: User, project_id: uuid.UUID, suffix: str) -> ProjectDetail:
        original = self._owned(user, project_id)
        name = f"{original.name} {suffix}"[:120]
        copy = self.projects.add(ProjectPrototype(original).clone(name))
        return self.get(user, copy.id)

    def delete(self, user: User, project_id: uuid.UUID) -> None:
        self.projects.delete(self._owned(user, project_id))

    def list_versions(self, user: User, project_id: uuid.UUID) -> list[VersionSummary]:
        self._owned(user, project_id)
        return [self._version(version) for version in self.versions.list_by_project(project_id)]

    def save_version(self, user: User, project_id: uuid.UUID, label: str) -> VersionDetail:
        project = self._owned(user, project_id)
        memento = ProjectSceneOriginator(project).create_memento(label.strip())
        version = ProjectSceneOriginator.to_version(project, memento)
        self.session.add(version)
        self.session.flush()
        self.versions.keep_latest(project.id, self.settings.scene_versions_limit)
        self.session.commit()
        return self._version(version, with_scene=True)

    def get_version(self, user: User, project_id: uuid.UUID, version_id: int) -> VersionDetail:
        self._owned(user, project_id)
        return self._version(self._owned_version(project_id, version_id), with_scene=True)

    def restore_version(self, user: User, project_id: uuid.UUID, version_id: int) -> ProjectDetail:
        project = self._owned(user, project_id)
        ProjectLifecycle(project).edit()
        memento = ProjectSceneOriginator.from_version(self._owned_version(project_id, version_id))
        ProjectSceneOriginator(project).restore(memento)
        self.session.commit()
        return self.get(user, project_id)

    def estimate(self, scene: dict) -> float:
        ids = walk_scene(scene, FurnitureIdCollector()).ids
        visitor = BudgetVisitor(
            self.furniture.prices_by_id(ids), self.materials.prices_by_slug(), self.addons.prices_by_slug()
        )
        return round(walk_scene(scene, visitor).total, 2)

    def _starter_scene(self, style, room_type, furnished: bool) -> dict:
        settings = self.settings
        builder = RoomBuilder(settings.room_default_width, settings.room_default_length, settings.room_default_height)
        if style is not None:
            by_surface = {material.surface: material.slug for material in reversed(style.materials)}
            builder.with_walls(by_surface.get("wall")).with_floor(by_surface.get("floor"))
            builder.with_lighting(style.lighting_color, style.lighting_intensity)
        if furnished and room_type is not None:
            StarterLayoutDirector(builder).furnish(self._starter_items(room_type.slug))
        scene = builder.build()
        scene["style"] = style.slug if style else None
        return scene

    def _starter_items(self, room_slug: str):
        chosen = {}
        for item in self.furniture.list_active():
            if room_slug in (item.category.room_types or []) and item.category.slug not in chosen:
                chosen[item.category.slug] = item
        return list(chosen.values())

    def _owned(self, user: User, project_id: uuid.UUID) -> Project:
        project = self.projects.get_owned(project_id, user.id)
        if project is None:
            raise ProjectNotFound
        return project

    def _owned_version(self, project_id: uuid.UUID, version_id: int) -> SceneVersion:
        version = self.versions.get_for_project(version_id, project_id)
        if version is None:
            raise ProjectNotFound
        return version

    def _style(self, slug: str):
        style = self.styles.get_by_slug(slug)
        if style is None or not style.is_active:
            raise ProjectInputError("Elige un estilo de la lista")
        return style

    def _room_type(self, slug: str):
        room_type = self.room_types.get_by_slug(slug)
        if room_type is None or not room_type.is_active:
            raise ProjectInputError("Elige un tipo de habitación de la lista")
        return room_type

    @staticmethod
    def _detail(project: Project) -> ProjectDetail:
        latest = project.redesigns[0] if project.redesigns else None
        return ProjectDetail(
            id=project.id,
            name=project.name,
            status=project.status,
            actions=ProjectLifecycle(project).actions,
            style=NamedRef(slug=project.style.slug, name=project.style.name) if project.style else None,
            room_type=NamedRef(slug=project.room_type.slug, name=project.room_type.name) if project.room_type else None,
            estimated_budget=project.estimated_budget,
            scene=project.scene or {},
            cover_image_url=(latest.result_image_url or latest.original_image_url) if latest else None,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    @staticmethod
    def _version(version: SceneVersion, with_scene: bool = False):
        memento = ProjectSceneOriginator.from_version(version)
        fields = {
            "id": version.id,
            "label": version.label,
            "estimated_budget": memento.estimated_budget,
            "items": walk_scene(memento.scene, FurnitureIdCollector()).count,
            "created_at": version.created_at,
        }
        return VersionDetail(**fields, scene=memento.scene) if with_scene else VersionSummary(**fields)
