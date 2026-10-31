import hashlib
import logging
import time
from collections import OrderedDict

from app.patterns.ai.ai_provider import ImageData, ImageEditor

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
