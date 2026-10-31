import uuid

from fastapi import APIRouter, HTTPException, Response, status

from app.dependencies import DbSession
from app.models import StoredFile

router = APIRouter(prefix="/files", tags=["Files"])


@router.get("/{file_id}", response_class=Response)
def read_file(file_id: uuid.UUID, db: DbSession) -> Response:
    stored = db.get(StoredFile, file_id)
    if stored is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Archivo no encontrado")
    return Response(
        stored.data,
        media_type=stored.content_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable", "Cross-Origin-Resource-Policy": "cross-origin"},
    )
