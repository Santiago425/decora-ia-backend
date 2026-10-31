from __future__ import annotations

import io
from dataclasses import dataclass, field

from PIL import Image, ImageOps, ImageStat, UnidentifiedImageError

from app.core.settings import get_settings

SIGNATURES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
}


class ImageValidationError(Exception):
    pass


@dataclass
class UploadedImage:
    data: bytes
    declared_type: str | None = None
    content_type: str | None = None
    image: Image.Image | None = field(default=None, repr=False)


# Chain of Responsibility: each validator checks one rule and passes the image to the next one or rejects it.
class ImageValidator:
    def __init__(self) -> None:
        self._next: ImageValidator | None = None

    def then(self, validator: ImageValidator) -> ImageValidator:
        self._next = validator
        return validator

    def validate(self, upload: UploadedImage) -> UploadedImage:
        self.check(upload)
        return self._next.validate(upload) if self._next else upload

    def check(self, upload: UploadedImage) -> None:
        raise NotImplementedError


class FormatValidator(ImageValidator):
    def check(self, upload: UploadedImage) -> None:
        head = upload.data[:12]
        content_type = next((kind for sig, kind in SIGNATURES.items() if head.startswith(sig)), None)
        if content_type is None and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
            content_type = "image/webp"
        if content_type is None:
            raise ImageValidationError("Sube una foto en formato JPG, PNG o WEBP")
        upload.content_type = content_type


class SizeValidator(ImageValidator):
    def __init__(self, max_mb: float) -> None:
        super().__init__()
        self.max_bytes = int(max_mb * 1024 * 1024)
        self.max_mb = max_mb

    def check(self, upload: UploadedImage) -> None:
        if len(upload.data) > self.max_bytes:
            raise ImageValidationError(f"La foto pesa demasiado. El máximo es {self.max_mb:g} MB")


class ResolutionValidator(ImageValidator):
    def __init__(self, min_side: int) -> None:
        super().__init__()
        self.min_side = min_side

    def check(self, upload: UploadedImage) -> None:
        try:
            image = Image.open(io.BytesIO(upload.data))
            image.load()
        except (UnidentifiedImageError, OSError):
            raise ImageValidationError("No pudimos abrir la foto. Prueba con otra imagen") from None
        image = ImageOps.exif_transpose(image)
        if min(image.size) < self.min_side:
            raise ImageValidationError(f"La foto es muy pequeña. Usa una de al menos {self.min_side} px por lado")
        upload.image = image


class ContentValidator(ImageValidator):
    MAX_ASPECT_RATIO = 3
    MIN_DETAIL = 6

    def check(self, upload: UploadedImage) -> None:
        width, height = upload.image.size
        if max(width, height) / min(width, height) > self.MAX_ASPECT_RATIO:
            raise ImageValidationError("La foto es demasiado alargada. Toma una foto completa del espacio")
        detail = ImageStat.Stat(upload.image.convert("L").resize((64, 64))).stddev[0]
        if detail < self.MIN_DETAIL:
            raise ImageValidationError("La foto parece vacía o de un solo color. Toma una foto del espacio")


def build_image_validation_chain() -> ImageValidator:
    settings = get_settings()
    chain = FormatValidator()
    chain.then(SizeValidator(settings.max_upload_mb)).then(ResolutionValidator(settings.min_image_side)).then(
        ContentValidator()
    )
    return chain
