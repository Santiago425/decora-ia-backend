from fastapi.testclient import TestClient


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_dashboard_requires_a_session(client: TestClient):
    assert client.get("/api/v1/dashboard").status_code == 401


def test_dashboard_summarizes_demo_projects(client: TestClient, user_token: str):
    body = client.get("/api/v1/dashboard", headers=auth(user_token)).json()
    stats = body["stats"]
    assert stats["projects"] == 4
    assert stats["redesigns"] == 3
    assert stats["favorite_style"]["slug"] == "nordic"
    assert float(stats["total_budget"]) == 6850000 + 4320000 + 3790000 + 2950000
    assert body["style_usage"][0] == {"slug": "nordic", "name": "Nórdico", "count": 2}
    assert body["recent_projects"][0]["name"] == "Sala luminosa"
    assert body["recent_projects"][0]["after_image_url"]
    assert body["recent_activity"][0]["kind"] == "redesign"


def test_new_user_gets_an_empty_dashboard(client: TestClient):
    session = client.post(
        "/api/v1/auth/register", json={"full_name": "Nuevo", "email": "nuevo@example.com", "password": "secreta123"}
    ).json()
    body = client.get("/api/v1/dashboard", headers=auth(session["access_token"])).json()
    assert body["stats"] == {"projects": 0, "redesigns": 0, "favorite_style": None, "total_budget": "0"}
    assert body["recent_projects"] == []
