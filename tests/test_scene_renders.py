from fastapi.testclient import TestClient

from app.models import DaylightPreset, DesignStyle, Material, RoomType
from app.patterns.adapters.scene_prompt_adapter import ScenePromptAdapter
from app.patterns.ai.ai_provider import AIError
from tests.test_projects_api import auth, designer, project  # noqa: F401


def upload(client: TestClient, headers: dict, project_id: str, photo: bytes):
    files = {"image": ("capture.jpg", photo, "image/jpeg")}
    return client.post(f"/api/v1/projects/{project_id}/renders", files=files, headers=headers)


def test_adapter_describes_the_scene_for_the_image_model():
    scene = {
        "room": {"wall_material": "wall_sage", "floor_material": None},
        "lighting": {"time_of_day": "night"},
        "nodes": [
            {"kind": "item", "shape": "sofa"},
            {"kind": "group", "children": [{"kind": "item", "shape": "chair"}, {"kind": "item", "shape": "chair"}]},
            {"kind": "item", "shape": "tv_stand"},
        ],
    }
    materials = {"wall_sage": Material(slug="wall_sage", name="Verde salvia", color_hex="#9caf88")}
    night = DaylightPreset(slug="night", prompt="night with lamps on")
    prompt = ScenePromptAdapter(
        scene, RoomType(slug="living_room"), DesignStyle(slug="mid-century"), materials, night
    ).prompt()
    assert "3D render of a living room in mid century style" in prompt
    assert "2 chairs" in prompt and "a sofa" in prompt and "a tv stand" in prompt
    assert "Verde salvia (#9caf88)" in prompt
    assert "Floor made of" not in prompt
    assert "night with lamps on" in prompt


def test_adapter_falls_back_to_soft_light_without_a_time_of_day():
    prompt = ScenePromptAdapter({}, None, None, {}, None).prompt()
    assert "3D render of a room into" in prompt
    assert "soft natural interior light" in prompt


def test_render_turns_the_capture_into_a_photo(client: TestClient, designer: dict, project: dict, photo):  # noqa: F811
    scene = project["scene"]
    scene["lighting"]["time_of_day"] = "afternoon"
    client.put(f"/api/v1/projects/{project['id']}/scene", json={"scene": scene}, headers=designer)

    response = upload(client, designer, project["id"], photo)
    assert response.status_code == 201
    render = response.json()
    assert render["status"] == "ready"
    assert render["time_of_day"] == "afternoon"
    assert render["result_image_url"] and render["result_image_url"] != render["capture_image_url"]
    assert "prompt" not in render

    listed = client.get(f"/api/v1/projects/{project['id']}/renders", headers=designer).json()
    assert [item["id"] for item in listed] == [render["id"]]
    detail = client.get(f"/api/v1/projects/{project['id']}", headers=designer).json()
    assert detail["cover_image_url"] is None


def test_render_reports_an_ai_failure(client: TestClient, designer: dict, project: dict, photo, monkeypatch):  # noqa: F811
    from app.patterns.ai.ai_client import AIClient

    def broken(image, prompt):
        raise AIError("La IA alcanzó su límite por ahora")

    monkeypatch.setattr(AIClient().image_editor, "edit", broken)
    render = upload(client, designer, project["id"], photo).json()
    assert render["status"] == "error"
    assert render["result_image_url"] is None
    assert "límite" in render["error_message"]


def test_render_is_private_and_checks_the_image(client: TestClient, designer: dict, project: dict, user_token):  # noqa: F811
    stranger = auth(user_token)
    assert upload(client, stranger, project["id"], b"not an image").status_code == 404
    assert client.get(f"/api/v1/projects/{project['id']}/renders", headers=stranger).status_code == 404
    assert upload(client, designer, project["id"], b"not an image").status_code == 422
