import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.settings import get_settings
from app.dependencies import CurrentUser
from app.models import Redesign
from app.patterns.ai.ai_client import AIClient
from app.patterns.ai.ai_provider import AIError
from app.patterns.builders.redesign_request_builder import RedesignRequestError
from app.patterns.facades.redesign_facade import RedesignFacade, RedesignNotFound, RedesignOptions
from app.patterns.storage.storage_adapter import create_storage
from app.patterns.strategies.budget_strategies import select_budget_strategy
from app.patterns.strategies.edit_strategies import EDIT_STRATEGIES, EditRequestError
from app.patterns.validators.image_validators import ImageValidationError
from app.repositories import MaterialRepository
from app.schemas.redesign import (
    EditFieldOption,
    EditFieldResponse,
    EditRequest,
    EditToolResponse,
    NamedRef,
    RedesignResponse,
    VariationRequest,
)

router = APIRouter(prefix="/redesigns", tags=["Redesigns"])
settings = get_settings()


def get_redesign_facade(db: Annotated[Session, Depends(get_db)]) -> RedesignFacade:
    try:
        ai = AIClient()
    except AIError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, error.user_message) from None
    return RedesignFacade(db, create_storage(db), ai)


Facade = Annotated[RedesignFacade, Depends(get_redesign_facade)]


def to_response(redesign: Redesign) -> RedesignResponse:
    project = redesign.project
    tool = EDIT_STRATEGIES.get(redesign.edit_tool or "")
    budget = float(redesign.budget) if redesign.budget is not None else None
    return RedesignResponse(
        id=redesign.id,
        project_id=project.id,
        project_name=project.name,
        status=redesign.status,
        style=NamedRef(slug=redesign.style.slug, name=redesign.style.name) if redesign.style else None,
        room_type=NamedRef(slug=project.room_type.slug, name=project.room_type.name) if project.room_type else None,
        original_image_url=redesign.original_image_url,
        result_image_url=redesign.result_image_url,
        palette=redesign.palette or [],
        budget=redesign.budget,
        budget_tier=select_budget_strategy(budget, settings.budget_economic_max, settings.budget_standard_max).key,
        keep_structure=redesign.keep_structure,
        keep_items=redesign.keep_items,
        edit_tool=NamedRef(slug=tool.key, name=tool.label) if tool else None,
        suggestions=redesign.suggestions or {},
        estimated_total=project.estimated_budget,
        error_message=redesign.error_message,
        created_at=redesign.created_at,
    )


def parse_palette(raw: str | None) -> list[str]:
    return [color.strip() for color in (raw or "").split(",") if color.strip()]


@router.post("", response_model=RedesignResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.redesign_rate_limit)
def create_redesign(
    request: Request,
    user: CurrentUser,
    facade: Facade,
    image: Annotated[UploadFile, File()],
    room_type: Annotated[str, Form(max_length=40)],
    style: Annotated[str, Form(max_length=40)],
    palette: Annotated[str | None, Form(max_length=120)] = None,
    budget: Annotated[float | None, Form(ge=0, le=10_000_000_000)] = None,
    keep_structure: Annotated[bool, Form()] = True,
    project_id: Annotated[uuid.UUID | None, Form()] = None,
    keep_items: Annotated[str | None, Form(max_length=200)] = None,
):
    max_bytes = int(settings.max_upload_mb * 1024 * 1024)
    photo = image.file.read(max_bytes + 1)
    options = RedesignOptions(room_type, style, parse_palette(palette), budget, keep_structure, project_id, keep_items)
    try:
        return to_response(facade.create_redesign(user, photo, image.content_type, options))
    except (ImageValidationError, RedesignRequestError) as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from None
    except RedesignNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontramos ese proyecto") from None


@router.get("", response_model=list[RedesignResponse])
def list_redesigns(project_id: Annotated[uuid.UUID, Query()], user: CurrentUser, facade: Facade):
    try:
        return [to_response(redesign) for redesign in facade.list_for_project(user, project_id)]
    except RedesignNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontramos ese proyecto") from None


@router.get("/edit-tools", response_model=list[EditToolResponse])
def list_edit_tools(user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    materials = MaterialRepository(db)
    return [
        EditToolResponse(
            key=tool.key,
            label=tool.label,
            description=tool.description,
            fields=[
                EditFieldResponse(
                    key=field.key,
                    label=field.label,
                    kind=field.kind,
                    placeholder=field.placeholder,
                    options=[
                        EditFieldOption(slug=m.slug, name=m.name, color_hex=m.color_hex, texture_url=m.texture_url)
                        for m in (materials.list_by_surface(field.surface) if field.kind == "material" else [])
                    ],
                )
                for field in tool.fields
            ],
        )
        for tool in EDIT_STRATEGIES.values()
    ]


@router.get("/{redesign_id}", response_model=RedesignResponse)
def get_redesign(redesign_id: uuid.UUID, user: CurrentUser, facade: Facade):
    try:
        return to_response(facade.get(user, redesign_id))
    except RedesignNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontramos ese rediseño") from None


@router.post("/{redesign_id}/variations", response_model=RedesignResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.redesign_rate_limit)
def create_variation(
    request: Request,
    redesign_id: uuid.UUID,
    user: CurrentUser,
    facade: Facade,
    options: Annotated[VariationRequest | None, Body()] = None,
):
    changes = options.model_dump(exclude_unset=True) if options else {}
    if changes.get("style") is None:
        changes.pop("style", None)
    if changes.get("keep_structure") is None:
        changes.pop("keep_structure", None)
    if "palette" in changes and changes["palette"] is None:
        changes["palette"] = []
    try:
        return to_response(facade.create_variation(user, redesign_id, changes))
    except RedesignNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontramos ese rediseño") from None
    except RedesignRequestError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from None


@router.post("/{redesign_id}/edits", response_model=RedesignResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.redesign_rate_limit)
def apply_edit(request: Request, redesign_id: uuid.UUID, user: CurrentUser, facade: Facade, body: EditRequest):
    try:
        return to_response(facade.apply_edit(user, redesign_id, body.tool, body.values))
    except RedesignNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontramos ese rediseño") from None
    except EditRequestError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from None


@router.post("/{redesign_id}/retry", response_model=RedesignResponse)
@limiter.limit(settings.redesign_rate_limit)
def retry_redesign(request: Request, redesign_id: uuid.UUID, user: CurrentUser, facade: Facade):
    try:
        return to_response(facade.retry(user, redesign_id))
    except RedesignNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontramos ese rediseño") from None
