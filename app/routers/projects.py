import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import CurrentUser, get_project_service
from app.patterns.states.project_states import ProjectTransitionError
from app.schemas.common import MessageResponse
from app.schemas.dashboard import ProjectSummary
from app.schemas.project import (
    ProjectCreate,
    ProjectDetail,
    ProjectUpdate,
    SceneUpdate,
    StatusChange,
    VersionCreate,
    VersionDetail,
    VersionSummary,
)
from app.services.project_service import (
    ProjectInputError,
    ProjectNotFound,
    ProjectService,
)

router = APIRouter(prefix="/projects", tags=["Projects"])
Service = Annotated[ProjectService, Depends(get_project_service)]
COPY_SUFFIX = "(copia)"


def handle(action):
    try:
        return action()
    except ProjectNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontramos ese proyecto") from None
    except ProjectInputError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, error.user_message) from None
    except ProjectTransitionError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, error.user_message) from None


@router.get("", response_model=list[ProjectSummary])
def list_projects(user: CurrentUser, service: Service):
    return service.list_for(user)


@router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_project(data: ProjectCreate, user: CurrentUser, service: Service):
    return handle(lambda: service.create(user, data))


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: uuid.UUID, user: CurrentUser, service: Service):
    return handle(lambda: service.get(user, project_id))


@router.patch("/{project_id}", response_model=ProjectDetail)
def update_project(project_id: uuid.UUID, data: ProjectUpdate, user: CurrentUser, service: Service):
    return handle(lambda: service.update(user, project_id, data))


@router.delete("/{project_id}", response_model=MessageResponse)
def delete_project(project_id: uuid.UUID, user: CurrentUser, service: Service):
    handle(lambda: service.delete(user, project_id))
    return MessageResponse(message="Proyecto eliminado")


@router.put("/{project_id}/scene", response_model=ProjectDetail)
def save_scene(project_id: uuid.UUID, data: SceneUpdate, user: CurrentUser, service: Service):
    return handle(lambda: service.save_scene(user, project_id, data.scene))


@router.post("/{project_id}/status", response_model=ProjectDetail)
def change_status(project_id: uuid.UUID, data: StatusChange, user: CurrentUser, service: Service):
    return handle(lambda: service.change_status(user, project_id, data.action))


@router.post("/{project_id}/duplicate", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def duplicate_project(project_id: uuid.UUID, user: CurrentUser, service: Service):
    return handle(lambda: service.duplicate(user, project_id, COPY_SUFFIX))


@router.get("/{project_id}/versions", response_model=list[VersionSummary])
def list_versions(project_id: uuid.UUID, user: CurrentUser, service: Service):
    return handle(lambda: service.list_versions(user, project_id))


@router.post("/{project_id}/versions", response_model=VersionDetail, status_code=status.HTTP_201_CREATED)
def save_version(project_id: uuid.UUID, data: VersionCreate, user: CurrentUser, service: Service):
    return handle(lambda: service.save_version(user, project_id, data.label))


@router.get("/{project_id}/versions/{version_id}", response_model=VersionDetail)
def get_version(project_id: uuid.UUID, version_id: int, user: CurrentUser, service: Service):
    return handle(lambda: service.get_version(user, project_id, version_id))


@router.post("/{project_id}/versions/{version_id}/restore", response_model=ProjectDetail)
def restore_version(project_id: uuid.UUID, version_id: int, user: CurrentUser, service: Service):
    return handle(lambda: service.restore_version(user, project_id, version_id))
