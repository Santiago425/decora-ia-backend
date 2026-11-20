import base64
import io

import pytest
from huggingface_hub.errors import HfHubHTTPError
from PIL import Image

from app.patterns.ai.ai_decorators import CachingImageEditor, FallbackImageEditor, UnchangedImageGuard
from app.patterns.ai.ai_provider import AIError, ImageData, ImageEditor
from app.patterns.ai.cloudflare_adapter import CloudflareImageEditor
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


class FakeResponse:
    def __init__(self, status_code: int, content: bytes, content_type: str) -> None:
        self.status_code = status_code
        self.content = content
        self.headers = {"content-type": content_type}


def test_cloudflare_sends_resized_photo_and_returns_image(monkeypatch):
    sent = {}

    def fake_post(url, headers, json, timeout):
        sent.update(url=url, json=json)
        return FakeResponse(200, b"png-bytes", "image/png")

    monkeypatch.setattr("app.patterns.ai.cloudflare_adapter.httpx.post", fake_post)
    editor = CloudflareImageEditor("acc", "token", "https://api.test/v4", "@cf/model", 0.6, 160, 30)
    result = editor.edit(_photo(), "japandi living room")
    assert sent["url"] == "https://api.test/v4/accounts/acc/ai/run/@cf/model"
    sent_image = Image.open(io.BytesIO(base64.b64decode(sent["json"]["image_b64"])))
    assert sent_image.size == (160, 120)
    assert result == ImageData(b"png-bytes", "image/png")


def test_cloudflare_error_raises_ai_error(monkeypatch):
    monkeypatch.setattr(
        "app.patterns.ai.cloudflare_adapter.httpx.post",
        lambda *args, **kwargs: FakeResponse(401, b"{}", "application/json"),
    )
    editor = CloudflareImageEditor("acc", "token", "https://api.test/v4", "@cf/model", 0.6, 768, 30)
    with pytest.raises(AIError):
        editor.edit(_photo(), "boho bedroom")


class CopyEditor(ImageEditor):
    name = "copy"

    def edit(self, image: ImageData, prompt: str) -> ImageData:
        return image


def test_unchanged_result_is_reported_as_error():
    with pytest.raises(AIError, match="sin cambios"):
        UnchangedImageGuard(CopyEditor(), 2.0).edit(_photo(), "nordic living room")


def test_changed_result_passes_the_guard():
    result = UnchangedImageGuard(MockImageEditor(), 2.0).edit(_photo(), "nordic living room")
    assert result.content_type == "image/jpeg"


class FakeHttpError(HfHubHTTPError):
    def __init__(self, status_code: int) -> None:
        Exception.__init__(self, f"HTTP {status_code}")
        self.response = type("Response", (), {"status_code": status_code})()


def test_huggingface_retries_when_provider_is_busy(monkeypatch):
    editor = HuggingFaceImageEditor("hf_test", "auto", "model", 30, retries=1, retry_delay=0)
    calls = []

    def flaky(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise FakeHttpError(503)
        return Image.new("RGB", (64, 64), "#2f5d50")

    monkeypatch.setattr(editor.client, "image_to_image", flaky)
    assert editor.edit(_photo(), "boho bedroom").content_type == "image/jpeg"
    assert len(calls) == 2


def test_huggingface_explains_missing_credits_without_retrying(monkeypatch):
    editor = HuggingFaceImageEditor("hf_test", "auto", "model", 30, retries=2, retry_delay=0)
    calls = []

    def no_credits(*args, **kwargs):
        calls.append(1)
        raise FakeHttpError(402)

    monkeypatch.setattr(editor.client, "image_to_image", no_credits)
    with pytest.raises(AIError, match="créditos"):
        editor.edit(_photo(), "boho bedroom")
    assert len(calls) == 1


def test_backup_copy_is_not_cached():
    calls = []

    class CountingBroken(BrokenEditor):
        def edit(self, image: ImageData, prompt: str) -> ImageData:
            calls.append(1)
            return super().edit(image, prompt)

    editor = FallbackImageEditor(CachingImageEditor(CountingBroken(), 4), MockImageEditor())
    editor.edit(_photo(), "nordic")
    editor.edit(_photo(), "nordic")
    assert len(calls) == 2
