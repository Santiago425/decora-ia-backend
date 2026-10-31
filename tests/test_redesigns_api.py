import base64

import httpx
import pytest
from fastapi.testclient import TestClient

from app.patterns.ai.ai_provider import AIError, ImageData
from app.patterns.ai.gemini_adapter import GeminiClient, GeminiDesignAdvisor, GeminiImageEditor


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def create(client, token, photo, **fields):
    data = {"room_type": "living_room", "style": "industrial", "budget": "2500000", "palette": "#2b2b2b,#c9c3b8"}
    data.update(fields)
    return client.post(
        "/api/v1/redesigns", headers=auth(token), data=data, files={"image": ("room.jpg", photo, "image/jpeg")}
    )


def test_redesign_requires_a_session(client: TestClient, photo):
    response = client.post("/api/v1/redesigns", data={"room_type": "bedroom", "style": "nordic"}, files={"image": ("r.jpg", photo)})
    assert response.status_code == 401


def test_full_redesign_flow_with_mock_ai(client: TestClient, user_token, photo):
    response = create(client, user_token, photo)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ready"
    assert body["style"] == {"slug": "industrial", "name": "Industrial"}
    assert body["budget_tier"] == "economic"
    assert body["palette"] == ["#2b2b2b", "#c9c3b8"]
    assert body["suggestions"]["furniture"]
    assert float(body["estimated_total"]) > 0

    for url in (body["original_image_url"], body["result_image_url"]):
        image = client.get(url)
        assert image.status_code == 200 and image.headers["content-type"] == "image/jpeg"

    variation = client.post(f"/api/v1/redesigns/{body['id']}/variations", headers=auth(user_token)).json()
    assert variation["project_id"] == body["project_id"]
    assert variation["original_image_url"] == body["original_image_url"]
    assert variation["id"] != body["id"]


def test_invalid_image_and_options_are_rejected(client: TestClient, user_token, photo):
    assert create(client, user_token, b"not an image").status_code == 422
    response = create(client, user_token, photo, style="gothic")
    assert response.status_code == 422 and "estilo" in response.json()["detail"]


def test_redesign_belongs_to_its_owner(client: TestClient, user_token, photo):
    redesign_id = create(client, user_token, photo).json()["id"]
    other = client.post(
        "/api/v1/auth/register", json={"full_name": "Otro", "email": "otro@example.com", "password": "secreta123"}
    ).json()["access_token"]
    assert client.get(f"/api/v1/redesigns/{redesign_id}", headers=auth(other)).status_code == 404


def test_ai_failure_is_saved_as_error_and_can_be_retried(client: TestClient, user_token, photo, monkeypatch):
    from app.patterns.ai.ai_client import AIClient

    editor = AIClient().image_editor

    def broken(image, prompt):
        raise AIError("La IA alcanzó su límite por ahora")

    monkeypatch.setattr(editor, "edit", broken)
    failed = create(client, user_token, photo, style="boho").json()
    assert failed["status"] == "error" and "límite" in failed["error_message"]

    monkeypatch.undo()
    retried = client.post(f"/api/v1/redesigns/{failed['id']}/retry", headers=auth(user_token)).json()
    assert retried["status"] == "ready" and retried["error_message"] is None


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def test_gemini_adapter_translates_the_api_format(monkeypatch):
    image_b64 = base64.b64encode(b"png-bytes").decode()
    replies = iter(
        [
            FakeResponse(200, {"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "image/png", "data": image_b64}}]}}]}),
            FakeResponse(200, {"candidates": [{"content": {"parts": [{"text": '{"summary": "Hola", "colors": [{"name": "Arena", "hex": "#e3d3bb"}]}'}]}}]}),
            FakeResponse(429, {}),
        ]
    )
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: next(replies))
    client = GeminiClient("key", "https://example.test/v1beta", 5)
    image = ImageData(b"jpg", "image/jpeg")

    assert GeminiImageEditor(client, "image-model").edit(image, "prompt") == ImageData(b"png-bytes", "image/png")
    assert GeminiDesignAdvisor(client, "text-model").suggest(image, "prompt").colors[0].hex == "#e3d3bb"
    with pytest.raises(AIError, match="límite"):
        GeminiImageEditor(client, "image-model").edit(image, "prompt")


def test_gemini_requires_an_api_key():
    with pytest.raises(AIError, match="GEMINI_API_KEY"):
        GeminiClient("", "https://example.test", 5)
