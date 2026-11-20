import io
import uuid

from PIL import Image
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.models import SceneRender, User
from app.patterns.adapters.scene_prompt_adapter import ScenePromptAdapter
from app.patterns.ai.ai_client import AIClient
from app.patterns.ai.ai_provider import AIError, ImageData
from app.patterns.states.redesign_states import RedesignProcess
from app.patterns.storage.storage_adapter import StorageAdapter
from app.patterns.validators.image_validators import UploadedImage, build_image_validation_chain
from app.repositories import DaylightPresetRepository, MaterialRepository, ProjectRepository, SceneRenderRepository


class SceneRenderNotFound(Exception):
    pass


class SceneRenderService:
    """Turns a capture of the 3D editor into a photorealistic picture with the same image model as the redesigns."""

    def __init__(self, session: Session, storage: StorageAdapter, ai: AIClient) -> None:
        self.session = session
        self.storage = storage
        self.ai = ai
        self.settings = get_settings()
        self.projects = ProjectRepository(session)
        self.renders = SceneRenderRepository(session)
        self.materials = MaterialRepository(session)
        self.daylight = DaylightPresetRepository(session)

    def render(self, user: User, project_id: uuid.UUID, capture: bytes, declared_type: str | None) -> SceneRender:
        project = self._owned(user, project_id)
        upload = build_image_validation_chain().validate(UploadedImage(capture, declared_type))
        image = self._normalize(upload.image)
        scene = project.scene or {}
        slug = (scene.get("lighting") or {}).get("time_of_day")
        daylight = self.daylight.get_by_slug(slug) if slug else None
        materials = {material.slug: material for material in self.materials.list_by_surface()}
        render = SceneRender(
            project=project,
            capture_image_url=self.storage.save(image.data, image.content_type),
            prompt=ScenePromptAdapter(scene, project.room_type, project.style, materials, daylight).prompt(),
            time_of_day=daylight.slug if daylight else None,
        )
        self.session.add(render)
        # The render goes through the same states as a redesign: processing, then ready or error.
        process = RedesignProcess(render)
        process.start_processing()
        self.session.flush()
        try:
            result = self.ai.image_editor.edit(image, render.prompt)
            process.complete(self.storage.save(result.data, result.content_type))
        except AIError as error:
            process.fail(error.user_message)
        self.session.commit()
        self.session.refresh(render)
        return render

    def list_for_project(self, user: User, project_id: uuid.UUID) -> list[SceneRender]:
        project = self._owned(user, project_id)
        return self.renders.recent_by_project(project.id, self.settings.scene_renders_limit)

    def _owned(self, user: User, project_id: uuid.UUID):
        project = self.projects.get_owned(project_id, user.id)
        if project is None:
            raise SceneRenderNotFound
        return project

    def _normalize(self, image: Image.Image) -> ImageData:
        picture = image.convert("RGB")
        picture.thumbnail((self.settings.max_image_side, self.settings.max_image_side))
        buffer = io.BytesIO()
        picture.save(buffer, "JPEG", quality=90)
        return ImageData(buffer.getvalue(), "image/jpeg")
