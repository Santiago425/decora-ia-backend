import io

import pytest
from PIL import Image

from app.patterns.ai.ai_decorators import FallbackImageEditor
from app.patterns.ai.ai_provider import AIError, ImageData, ImageEditor
from app.patterns.ai.huggingface_adapter import HuggingFaceImageEditor
from app.patterns.ai.mock_adapter import MockImageEditor


def _photo() -> ImageData:
    buffer = io.BytesIO()
    Image.new("RGB", (320, 240), "#c4704f").save(buffer, "PNG")
    return ImageData(buffer.getvalue(), "image/png")


class BrokenEditor(ImageEditor):
    name = "broken"

    def edit(self, image: ImageData, prompt: str) -> ImageData:
        raise AIError("sin créditos")


def test_fallback_uses_backup_when_provider_fails():
    result = FallbackImageEditor(BrokenEditor(), MockImageEditor()).edit(_photo(), "nordic living room")
    assert result.content_type == "image/jpeg"
    assert Image.open(io.BytesIO(result.data)).size == (320, 240)


def test_huggingface_requires_token():
    with pytest.raises(AIError):
        HuggingFaceImageEditor("", "auto", "black-forest-labs/FLUX.1-Kontext-dev", 30)


def test_huggingface_converts_result_to_jpeg(monkeypatch):
    editor = HuggingFaceImageEditor("hf_test", "auto", "black-forest-labs/FLUX.1-Kontext-dev", 30)
    monkeypatch.setattr(editor.client, "image_to_image", lambda *args, **kwargs: Image.new("RGBA", (64, 64)))
    result = editor.edit(_photo(), "boho bedroom")
    assert result.content_type == "image/jpeg"
    assert Image.open(io.BytesIO(result.data)).size == (64, 64)
