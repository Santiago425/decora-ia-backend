import io
import uuid
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from PIL import Image
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.models import Project, ProjectStatus, Redesign, User
from app.patterns.ai.ai_client import AIClient
from app.patterns.ai.ai_provider import AIError, DesignSuggestions, ImageData, SuggestedColor, SuggestedItem
from app.patterns.builders.redesign_request_builder import RedesignRequest, RedesignRequestBuilder
from app.patterns.states.redesign_states import RedesignProcess
from app.patterns.storage.storage_adapter import StorageAdapter
from app.patterns.strategies.budget_strategies import BudgetStrategy, select_budget_strategy
from app.patterns.validators.image_validators import UploadedImage, build_image_validation_chain
from app.repositories import FurnitureRepository, ProjectRepository, RoomTypeRepository, StyleRepository

MAX_SUGGESTED_ITEMS = 5


class RedesignNotFound(Exception):
    pass


@dataclass
class RedesignOptions:
    room_type: str
    style: str
    palette: list[str]
    budget: float | None
    keep_structure: bool
    project_id: uuid.UUID | None = None


# Facade: one call hides validation, storage, the AI, suggestions, budget and project bookkeeping.
class RedesignFacade:
    def __init__(self, session: Session, storage: StorageAdapter, ai: AIClient) -> None:
        self.session = session
        self.storage = storage
        self.ai = ai
        self.settings = get_settings()
        self.projects = ProjectRepository(session)
        self.styles = StyleRepository(session)
        self.room_types = RoomTypeRepository(session)
        self.furniture = FurnitureRepository(session)

    def create_redesign(self, user: User, photo: bytes, declared_type: str | None, options: RedesignOptions) -> Redesign:
        upload = build_image_validation_chain().validate(UploadedImage(photo, declared_type))
        image = self._normalize(upload.image)
        style = self.styles.get_by_slug(options.style)
        room_type = self.room_types.get_by_slug(options.room_type)
        strategy = self._strategy(options.budget)
        request = (
            RedesignRequestBuilder(self.settings.currency_code)
            .with_photo(image)
            .for_room(room_type)
            .in_style(style)
            .with_palette(options.palette)
            .with_budget(options.budget, strategy)
            .keeping_structure(options.keep_structure)
            .build()
        )
        project = self._project_for(user, options.project_id, request)
        redesign = Redesign(
            project=project,
            style_id=style.id,
            original_image_url=self.storage.save(image.data, image.content_type),
            palette=list(request.palette),
            budget=Decimal(str(options.budget)) if options.budget is not None else None,
            keep_structure=options.keep_structure,
        )
        self.session.add(redesign)
        return self._run(redesign, request)

    def create_variation(self, user: User, redesign_id: uuid.UUID) -> Redesign:
        source = self._owned(user, redesign_id)
        request = self._request_from(source, variation=len(source.project.redesigns))
        variation = Redesign(
            project=source.project,
            style_id=source.style_id,
            original_image_url=source.original_image_url,
            palette=source.palette,
            budget=source.budget,
            keep_structure=source.keep_structure,
        )
        self.session.add(variation)
        return self._run(variation, request)

    def retry(self, user: User, redesign_id: uuid.UUID) -> Redesign:
        redesign = self._owned(user, redesign_id)
        return self._run(redesign, self._request_from(redesign, variation=0))

    def get(self, user: User, redesign_id: uuid.UUID) -> Redesign:
        return self._owned(user, redesign_id)

    def _run(self, redesign: Redesign, request: RedesignRequest) -> Redesign:
        process = RedesignProcess(redesign)
        process.start_processing()
        redesign.prompt = request.image_prompt()
        self.session.flush()
        try:
            result = self.ai.image_editor.edit(request.image, redesign.prompt)
            suggestions = self._suggestions(request)
            redesign.suggestions = suggestions.model_dump()
            project = redesign.project
            project.estimated_budget = Decimal(str(round(suggestions.total(), 2)))
            if project.status == ProjectStatus.DRAFT:
                project.status = ProjectStatus.IN_DESIGN
            process.complete(self.storage.save(result.data, result.content_type))
        except AIError as error:
            process.fail(error.user_message)
        self.session.commit()
        self.session.refresh(redesign)
        return redesign

    def _suggestions(self, request: RedesignRequest) -> DesignSuggestions:
        fallback = self._catalog_suggestions(request)
        try:
            return self.ai.advisor(fallback).suggest(request.image, request.advice_prompt())
        except AIError:
            return fallback

    def _catalog_suggestions(self, request: RedesignRequest) -> DesignSuggestions:
        by_category = defaultdict(list)
        for item in self.furniture.list_active():
            if request.room_type.slug in (item.category.room_types or []):
                by_category[item.category.slug].append(item)
        picks = request.budget_strategy.pick(by_category, MAX_SUGGESTED_ITEMS, request.budget)
        style = request.style
        colors = list(request.palette) or (style.palettes[0].colors if style.palettes else [])
        return DesignSuggestions(
            summary=f"Una propuesta {style.name.lower()} para tu {request.room_type.name.lower()}: {style.description}",
            furniture=[SuggestedItem(name=i.name, description=i.description, price=float(i.price)) for i in picks],
            colors=[SuggestedColor(name=f"Tono {n}", hex=c) for n, c in enumerate(colors[:5], start=1)],
            materials=[
                SuggestedItem(name=m.name, description=f"Para {self._surface(m.surface)}", price=float(m.price_per_unit))
                for m in style.materials
            ],
            lighting=[SuggestedItem(name="Luz cálida regulable", description="Lámparas de luz cálida para un ambiente acogedor")],
        )

    def _request_from(self, redesign: Redesign, variation: int) -> RedesignRequest:
        project = redesign.project
        budget = float(redesign.budget) if redesign.budget is not None else None
        return (
            RedesignRequestBuilder(self.settings.currency_code)
            .with_photo(self.storage.load(redesign.original_image_url))
            .for_room(project.room_type)
            .in_style(redesign.style)
            .with_palette(redesign.palette)
            .with_budget(budget, self._strategy(budget))
            .keeping_structure(redesign.keep_structure)
            .as_variation(variation)
            .build()
        )

    def _project_for(self, user: User, project_id: uuid.UUID | None, request: RedesignRequest) -> Project:
        if project_id:
            project = self.projects.get_owned(project_id, user.id)
            if project is None:
                raise RedesignNotFound
            return project
        project = Project(
            owner=user,
            name=f"{request.room_type.name} {request.style.name.lower()}",
            room_type_id=request.room_type.id,
            style_id=request.style.id,
        )
        self.session.add(project)
        return project

    def _owned(self, user: User, redesign_id: uuid.UUID) -> Redesign:
        redesign = self.session.get(Redesign, redesign_id)
        if redesign is None or redesign.project.user_id != user.id:
            raise RedesignNotFound
        return redesign

    def _strategy(self, budget: float | None) -> BudgetStrategy:
        return select_budget_strategy(budget, self.settings.budget_economic_max, self.settings.budget_standard_max)

    def _normalize(self, image: Image.Image) -> ImageData:
        picture = image.convert("RGB")
        picture.thumbnail((self.settings.max_image_side, self.settings.max_image_side))
        buffer = io.BytesIO()
        picture.save(buffer, "JPEG", quality=90)
        return ImageData(buffer.getvalue(), "image/jpeg")

    @staticmethod
    def _surface(surface: str) -> str:
        return {"wall": "paredes", "floor": "piso", "furniture": "muebles"}.get(surface, surface)
