import pytest
from fastapi.testclient import TestClient


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def designer(client: TestClient) -> dict:
    import uuid

    email = f"designer-{uuid.uuid4().hex[:8]}@example.com"
    session = client.post("/api/v1/auth/register", json={"full_name": "Diseñadora", "email": email, "password": "secreta123"})
    return auth(session.json()["access_token"])


@pytest.fixture
def project(client: TestClient, designer: dict) -> dict:
    body = {"name": "Sala de prueba", "room_type": "living_room", "style": "nordic"}
    response = client.post("/api/v1/projects", json=body, headers=designer)
    assert response.status_code == 201
    return response.json()


def test_new_project_starts_with_a_furnished_room(project: dict):
    scene = project["scene"]
    assert project["status"] == "draft"
    assert project["actions"] == ["start"]
    assert scene["room"]["wall_material"] == "wall_bone_white"
    assert scene["room"]["floor_material"] == "floor_light_oak"
    assert scene["style"] == "nordic"
    shapes = {node["shape"] for node in scene["nodes"]}
    assert "sofa" in shapes and "bed" not in shapes
    assert float(project["estimated_budget"]) > 0


def test_saving_the_scene_recalculates_the_budget_and_moves_to_design(client, designer, project):
    scene = project["scene"]
    sofa = next(node for node in scene["nodes"] if node["shape"] == "sofa")
    sofa["price"] = 1
    scene["nodes"] = [sofa]
    saved = client.put(f"/api/v1/projects/{project['id']}/scene", json={"scene": scene}, headers=designer).json()
    room = scene["room"]
    floor = room["width"] * room["length"] * 120000
    walls = 2 * (room["width"] + room["length"]) * room["height"] * 18000
    assert saved["status"] == "in_design"
    assert float(saved["estimated_budget"]) == pytest.approx(2890000 + floor + walls)

    sofa["addons"] = ["cushions"]
    saved = client.put(f"/api/v1/projects/{project['id']}/scene", json={"scene": scene}, headers=designer).json()
    assert float(saved["estimated_budget"]) == pytest.approx(2890000 + 120000 + floor + walls)


def test_groups_are_accepted_and_counted(client, designer, project):
    scene = project["scene"]
    scene["nodes"] = [{"kind": "group", "id": "g-1", "name": "Zona de estar", "children": scene["nodes"]}]
    response = client.put(f"/api/v1/projects/{project['id']}/scene", json={"scene": scene}, headers=designer)
    assert response.status_code == 200
    assert response.json()["scene"]["nodes"][0]["kind"] == "group"


def test_invalid_scene_is_rejected(client, designer, project):
    scene = project["scene"]
    scene["room"]["width"] = 100
    response = client.put(f"/api/v1/projects/{project['id']}/scene", json={"scene": scene}, headers=designer)
    assert response.status_code == 422


def test_finished_project_must_be_reopened_before_editing(client, designer, project):
    url = f"/api/v1/projects/{project['id']}"
    assert client.post(f"{url}/status", json={"action": "finish"}, headers=designer).status_code == 409
    assert client.post(f"{url}/status", json={"action": "start"}, headers=designer).json()["status"] == "in_design"
    finished = client.post(f"{url}/status", json={"action": "finish"}, headers=designer).json()
    assert finished["status"] == "finished" and finished["actions"] == ["reopen"]

    blocked = client.put(f"{url}/scene", json={"scene": project["scene"]}, headers=designer)
    assert blocked.status_code == 409
    assert "Reábrelo" in blocked.json()["detail"]
    assert client.post(f"{url}/status", json={"action": "reopen"}, headers=designer).json()["status"] == "in_design"


def test_versions_restore_an_earlier_scene(client, designer, project):
    url = f"/api/v1/projects/{project['id']}"
    original_count = len(project["scene"]["nodes"])
    version = client.post(f"{url}/versions", json={"label": "Primera idea"}, headers=designer).json()
    assert version["items"] == original_count

    emptied = {**project["scene"], "nodes": []}
    client.put(f"{url}/scene", json={"scene": emptied}, headers=designer)
    assert client.get(f"{url}/versions", headers=designer).json()[0]["label"] == "Primera idea"

    restored = client.post(f"{url}/versions/{version['id']}/restore", headers=designer).json()
    assert len(restored["scene"]["nodes"]) == original_count
    assert float(restored["estimated_budget"]) == float(project["estimated_budget"])


def test_duplicate_creates_an_independent_draft(client, designer, project):
    copy = client.post(f"/api/v1/projects/{project['id']}/duplicate", headers=designer).json()
    assert copy["id"] != project["id"]
    assert copy["name"] == "Sala de prueba (copia)"
    assert copy["status"] == "draft"
    original_ids = {node["id"] for node in project["scene"]["nodes"]}
    assert original_ids.isdisjoint(node["id"] for node in copy["scene"]["nodes"])
    assert len(client.get("/api/v1/projects", headers=designer).json()) == 2


def test_projects_are_private(client, designer, project, user_token):
    assert client.get(f"/api/v1/projects/{project['id']}", headers=auth(user_token)).status_code == 404
    assert client.delete(f"/api/v1/projects/{project['id']}", headers=designer).status_code == 200
    assert client.get(f"/api/v1/projects/{project['id']}", headers=designer).status_code == 404


def test_demo_project_without_scene_gets_one_on_open(client, user_token):
    projects = client.get("/api/v1/projects", headers=auth(user_token)).json()
    bedroom = next(p for p in projects if p["room_type_name"] == "Dormitorio")
    detail = client.get(f"/api/v1/projects/{bedroom['id']}", headers=auth(user_token)).json()
    assert any(node["shape"] == "bed" for node in detail["scene"]["nodes"])


def test_unknown_style_is_rejected(client, designer):
    body = {"name": "Otra", "room_type": "living_room", "style": "nope"}
    response = client.post("/api/v1/projects", json=body, headers=designer)
    assert response.status_code == 422
    assert response.json()["detail"] == "Elige un estilo de la lista"


def test_catalog_lists_furniture_addons(client):
    addons = client.get("/api/v1/catalog/addons").json()
    cushions = next(addon for addon in addons if addon["slug"] == "cushions")
    assert "sofa" in cushions["categories"]
    assert float(cushions["price"]) == 120000
