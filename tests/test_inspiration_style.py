import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.settings import Settings
from app.patterns.ai.ai_provider import AIError, ImageData, StyleDescription
from app.patterns.ai.gemini_adapter import GeminiClient, GeminiStyleDescriber
from app.patterns.ai.mock_adapter import MockStyleDescriber
from app.patterns.ai.provider_factories import factory_for
from tests.conftest import make_photo


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def create(client, token, photo):
    data = {"room_type": "living_room", "style": "industrial", "keep_items": "la lámpara de pie"}
    return client.post(
        "/api/v1/redesigns", headers=auth(token), data=data, files={"image": ("room.jpg", photo, "image/jpeg")}
    ).json()


def inspire(client, token, redesign_id, picture):
    return client.post(
        f"/api/v1/redesigns/{redesign_id}/inspiration",
        headers=auth(token),
        files={"image": ("inspiration.jpg", picture, "image/jpeg")},
    )


def test_inspiration_photo_creates_a_new_version_with_its_style(client: TestClient, user_token, photo):
    first = create(client, user_token, photo)
    response = inspire(client, user_token, first["id"], make_photo((900, 700)))
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ready"
    assert body["project_id"] == first["project_id"]
    assert body["original_image_url"] == first["original_image_url"]
    assert body["inspiration_name"] == "Inspiración"
    assert client.get(body["inspiration_image_url"]).status_code == 200
    assert body["palette"] and body["suggestions"]["colors"][0]["hex"] == body["palette"][0]
    assert body["keep_items"] == "la lámpara de pie"


def test_failed_inspiration_version_can_be_retried(client: TestClient, user_token, photo, monkeypatch):
    from app.patterns.ai.ai_client import AIClient

    first = create(client, user_token, photo)

    def broken(image, prompt):
        raise AIError("La IA alcanzó su límite por ahora")

    monkeypatch.setattr(AIClient().image_editor, "edit", broken)
    failed = inspire(client, user_token, first["id"], make_photo((640, 640))).json()
    assert failed["status"] == "error"

    monkeypatch.undo()
    retried = client.post(f"/api/v1/redesigns/{failed['id']}/retry", headers=auth(user_token)).json()
    assert retried["status"] == "ready" and retried["inspiration_image_url"] == failed["inspiration_image_url"]
    assert retried["original_image_url"] == first["original_image_url"]


def test_inspiration_validates_the_photo_and_the_owner(client: TestClient, user_token, photo):
    first = create(client, user_token, photo)
    assert inspire(client, user_token, first["id"], b"not an image").status_code == 422
    other = client.post(
        "/api/v1/auth/register", json={"full_name": "Ana", "email": "ana-insp@example.com", "password": "secreta123"}
    ).json()["access_token"]
    assert inspire(client, other, first["id"], make_photo()).status_code == 404


def test_describer_failure_returns_a_clear_message(client: TestClient, user_token, photo, monkeypatch):
    def broken(self, image):
        raise AIError("La IA no pudo leer el estilo de esa foto. Prueba con otra imagen")

    monkeypatch.setattr(MockStyleDescriber, "describe", broken)
    first = create(client, user_token, photo)
    response = inspire(client, user_token, first["id"], make_photo())
    assert response.status_code == 503 and "estilo" in response.json()["detail"]


def test_style_description_builds_the_image_prompt():
    description = StyleDescription(prompt="japandi, light oak and linen", colors=["#e3d3bb"])
    prompt = description.image_prompt(keep_structure=True, keep_items="el sofá")
    assert "japandi, light oak and linen" in prompt
    assert "Do not move, add or remove any window" in prompt
    assert "el sofá" in prompt and "#e3d3bb" in prompt
    assert "Do not move" not in description.image_prompt(keep_structure=False)


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def reply(text: str) -> FakeResponse:
    return FakeResponse(200, {"candidates": [{"content": {"parts": [{"text": text}]}}]})


def test_gemini_describer_adapts_the_api_answer(monkeypatch):
    answer = {
        "name": "Japandi",
        "summary": "Madera clara y lino.",
        "prompt": "japandi room with light oak and linen",
        "colors": ["#e3d3bb", "beige", "#2f5d50"],
    }
    replies = iter([reply(json.dumps(answer)), reply("not json")])
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: next(replies))
    describer = GeminiStyleDescriber(GeminiClient("key", "https://example.test/v1beta", 5), "text-model")
    image = ImageData(b"jpg", "image/jpeg")

    description = describer.describe(image)
    assert description.name == "Japandi"
    assert description.colors == ["#e3d3bb", "#2f5d50"]
    with pytest.raises(AIError, match="estilo"):
        describer.describe(image)


@pytest.mark.parametrize(("provider", "describer"), [("gemini", GeminiStyleDescriber), ("mock", MockStyleDescriber)])
def test_factories_build_the_style_describer(provider, describer):
    settings = Settings(gemini_api_key="key")
    assert isinstance(factory_for(provider, settings).create_style_describer(), describer)
    assert isinstance(factory_for("huggingface", settings).create_style_describer(), MockStyleDescriber)
