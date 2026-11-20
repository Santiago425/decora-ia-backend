import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import RedesignStatus


class SceneRenderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    status: RedesignStatus
    capture_image_url: str
    result_image_url: str | None
    time_of_day: str | None
    error_message: str | None
    created_at: datetime
