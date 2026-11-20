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
    response = client.post(
        "/api/v1/redesigns", data={"room_type": "bedroom", "style": "nordic"}, files={"image": ("r.jpg", photo)}
    )
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


def test_variation_can_change_style_palette_and_budget(client: TestClient, user_token, photo):
    first = create(client, user_token, photo).json()
    url = f"/api/v1/redesigns/{first['id']}/variations"
    second = client.post(
        url, headers=auth(user_token), json={"style": "nordic", "palette": ["#ffffff"], "budget": 90000000}
    ).json()
    assert second["status"] == "ready"
    assert second["style"]["slug"] == "nordic"
    assert second["palette"] == ["#ffffff"]
    assert second["budget_tier"] == "premium"
    assert second["original_image_url"] == first["original_image_url"]
    assert second["keep_structure"] is True

    history = client.get("/api/v1/redesigns", params={"project_id": first["project_id"]}, headers=auth(user_token))
    assert [item["id"] for item in history.json()] == [second["id"], first["id"]]
    projects = client.get("/api/v1/projects", headers=auth(user_token)).json()
    assert next(p for p in projects if p["id"] == first["project_id"])["style_name"] == "Nórdico"

    assert client.post(url, headers=auth(user_token), json={"style": "gothic"}).status_code == 422


def test_redesign_history_is_private(client: TestClient, user_token, photo):
    project_id = create(client, user_token, photo).json()["project_id"]
    other = client.post(
        "/api/v1/auth/register", json={"full_name": "Otra", "email": "otra@example.com", "password": "secreta123"}
    ).json()["access_token"]
    response = client.get("/api/v1/redesigns", params={"project_id": project_id}, headers=auth(other))
    assert response.status_code == 404


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
            FakeResponse(
                200,
                {
                    "candidates": [
                        {"content": {"parts": [{"inlineData": {"mimeType": "image/png", "data": image_b64}}]}}
                    ]
                },
            ),
            FakeResponse(
                200,
                {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {"text": '{"summary": "Hola", "colors": [{"name": "Arena", "hex": "#e3d3bb"}]}'}
                                ]
                            }
                        }
                    ]
                },
            ),
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


def test_edit_tools_are_listed_with_catalog_floors(client: TestClient, user_token):
    tools = {tool["key"]: tool for tool in client.get("/api/v1/redesigns/edit-tools", headers=auth(user_token)).json()}
    assert set(tools) == {"wall_paint", "floor_swap", "remove_object", "replace_furniture"}
    floors = tools["floor_swap"]["fields"][0]["options"]
    assert floors and all(option["slug"].startswith("floor_") for option in floors)


def test_targeted_edit_creates_a_new_version_from_the_result(client: TestClient, user_token, photo):
    first = create(client, user_token, photo, keep_items="el sillón de terciopelo").json()
    assert first["keep_items"] == "el sillón de terciopelo"
    url = f"/api/v1/redesigns/{first['id']}/edits"

    painted = client.post(url, headers=auth(user_token), json={"tool": "wall_paint", "values": {"color": "#A9B49A"}})
    assert painted.status_code == 201
    body = painted.json()
    assert body["status"] == "ready"
    assert body["edit_tool"] == {"slug": "wall_paint", "name": "Pintar paredes"}
    assert body["original_image_url"] == first["result_image_url"]
    assert body["suggestions"] == first["suggestions"]
    assert body["keep_items"] == "el sillón de terciopelo"

    floor = client.post(
        f"/api/v1/redesigns/{body['id']}/edits",
        headers=auth(user_token),
        json={"tool": "floor_swap", "values": {"material": "floor_walnut"}},
    )
    assert floor.status_code == 201

    history = client.get("/api/v1/redesigns", params={"project_id": first["project_id"]}, headers=auth(user_token))
    assert len(history.json()) == 3


def test_targeted_edit_validates_tool_and_fields(client: TestClient, user_token, photo):
    url = f"/api/v1/redesigns/{create(client, user_token, photo).json()['id']}/edits"
    cases = [
        {"tool": "teleport", "values": {}},
        {"tool": "wall_paint", "values": {"color": "verde"}},
        {"tool": "floor_swap", "values": {"material": "wall_lime"}},
        {"tool": "replace_furniture", "values": {"target": "el sofá"}},
    ]
    for payload in cases:
        assert client.post(url, headers=auth(user_token), json=payload).status_code == 422


def test_a_version_can_be_deleted_but_not_the_last_one(client: TestClient, user_token, photo):
    other_token = client.post(
        "/api/v1/auth/register", json={"full_name": "Otra", "email": "borra@example.com", "password": "secreta123"}
    ).json()["access_token"]
    first = create(client, user_token, photo).json()
    edited = client.post(
        f"/api/v1/redesigns/{first['id']}/edits",
        headers=auth(user_token),
        json={"tool": "wall_paint", "values": {"color": "#a9b49a"}},
    ).json()

    assert client.delete(f"/api/v1/redesigns/{first['id']}", headers=auth(other_token)).status_code == 404
    assert client.delete(f"/api/v1/redesigns/{first['id']}", headers=auth(user_token)).status_code == 204

    history = client.get("/api/v1/redesigns", params={"project_id": first["project_id"]}, headers=auth(user_token))
    assert [item["id"] for item in history.json()] == [edited["id"]]
    assert client.get(f"/api/v1/redesigns/{edited['id']}", headers=auth(user_token)).json()["result_image_url"]

    last = client.delete(f"/api/v1/redesigns/{edited['id']}", headers=auth(user_token))
    assert last.status_code == 409
