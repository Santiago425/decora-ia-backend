import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.models import StoredFile
from app.patterns.ai.ai_provider import ImageData

EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


# Adapter: the app saves files through one interface, whether they end up on disk or in the cloud database.
class StorageAdapter(ABC):
    @abstractmethod
    def save(self, data: bytes, content_type: str) -> str:
        """Stores the file and returns the public URL path to read it."""

    @abstractmethod
    def load(self, url: str) -> ImageData:
        """Reads back a file saved by this adapter."""


class LocalStorageAdapter(StorageAdapter):
    def __init__(self, directory: Path, url_path: str) -> None:
        self.directory = directory
        self.url_path = url_path.rstrip("/")
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes, content_type: str) -> str:
        name = f"{uuid.uuid4().hex}{EXTENSIONS.get(content_type, '.bin')}"
        (self.directory / name).write_bytes(data)
        return f"{self.url_path}/{name}"

    def load(self, url: str) -> ImageData:
        name = Path(url).name
        content_type = next((kind for kind, ext in EXTENSIONS.items() if name.endswith(ext)), "application/octet-stream")
        return ImageData((self.directory / name).read_bytes(), content_type)


class DatabaseStorageAdapter(StorageAdapter):
    def __init__(self, session: Session, api_prefix: str) -> None:
        self.session = session
        self.api_prefix = api_prefix

    def save(self, data: bytes, content_type: str) -> str:
        stored = StoredFile(content_type=content_type, size_bytes=len(data), data=data)
        self.session.add(stored)
        self.session.flush()
        return f"{self.api_prefix}/files/{stored.id}"

    def load(self, url: str) -> ImageData:
        stored = self.session.get(StoredFile, uuid.UUID(url.rsplit("/", 1)[-1]))
        if stored is None:
            raise FileNotFoundError(url)
        return ImageData(stored.data, stored.content_type)


def create_storage(session: Session) -> StorageAdapter:
    settings = get_settings()
    if settings.storage_provider == "database":
        return DatabaseStorageAdapter(session, settings.api_prefix)
    return LocalStorageAdapter(Path(settings.media_dir), settings.media_url_path)
