import hashlib
import io
import logging
import time
from collections import OrderedDict

from PIL import Image, ImageChops, ImageOps, ImageStat

from app.patterns.ai.ai_provider import AIError, ImageData, ImageEditor

logger = logging.getLogger("habita.ai")


# Decorator: adds behaviour to any ImageEditor without changing it.
class ImageEditorDecorator(ImageEditor):
    def __init__(self, inner: ImageEditor) -> None:
        self.inner = inner
        self.name = inner.name

    def edit(self, image: ImageData, prompt: str) -> ImageData:
        return self.inner.edit(image, prompt)


class LoggingImageEditor(ImageEditorDecorator):
    def edit(self, image: ImageData, prompt: str) -> ImageData:
        start = time.perf_counter()
        try:
            return super().edit(image, prompt)
        finally:
            logger.info("ai.edit provider=%s took=%.1fs", self.name, time.perf_counter() - start)


class UnchangedImageGuard(ImageEditorDecorator):
    """Reports an error when the model returns the same photo, instead of saving it as a finished design."""

    sample_side = 64

    def __init__(self, inner: ImageEditor, min_change: float) -> None:
        super().__init__(inner)
        self.min_change = min_change

    def edit(self, image: ImageData, prompt: str) -> ImageData:
        result = super().edit(image, prompt)
        change = self.difference(image, result)
        if change < self.min_change:
            logger.warning("ai.unchanged provider=%s change=%.2f", self.name, change)
            raise AIError("La IA devolvió la foto sin cambios. Prueba de nuevo o describe el cambio con más detalle")
        return result

    def difference(self, before: ImageData, after: ImageData) -> float:
        """Average pixel difference (0-255) between two photos, compared at the same small size."""
        size = (self.sample_side, self.sample_side)
        first, second = (
            ImageOps.exif_transpose(Image.open(io.BytesIO(item.data))).convert("RGB").resize(size)
            for item in (before, after)
        )
        return sum(ImageStat.Stat(ImageChops.difference(first, second)).mean) / 3


class CachingImageEditor(ImageEditorDecorator):
    def __init__(self, inner: ImageEditor, max_entries: int) -> None:
        super().__init__(inner)
        self.max_entries = max_entries
        self._cache: OrderedDict[str, ImageData] = OrderedDict()

    def edit(self, image: ImageData, prompt: str) -> ImageData:
        key = hashlib.sha256(image.data + prompt.encode()).hexdigest()
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        result = super().edit(image, prompt)
        self._cache[key] = result
        if len(self._cache) > self.max_entries:
            self._cache.popitem(last=False)
        return result


class FallbackImageEditor(ImageEditorDecorator):
    """Falls back to a backup editor when the main provider fails, so a redesign never ends empty."""

    def __init__(self, inner: ImageEditor, backup: ImageEditor) -> None:
        super().__init__(inner)
        self.backup = backup

    def edit(self, image: ImageData, prompt: str) -> ImageData:
        try:
            return super().edit(image, prompt)
        except AIError as error:
            logger.warning(
                "ai.fallback provider=%s backup=%s reason=%s", self.name, self.backup.name, error.user_message
            )
            return self.backup.edit(image, prompt)
