from fastapi.testclient import TestClient


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_favorites_need_a_session(client: TestClient):
    assert client.get("/api/v1/catalog/favorites").status_code == 401


def test_a_user_marks_and_unmarks_favorites(client: TestClient, user_token):
    headers = auth(user_token)
    first, second = (item["id"] for item in client.get("/api/v1/catalog/furniture").json()[:2])

    assert client.put(f"/api/v1/catalog/favorites/{first}", headers=headers).status_code == 204
    assert client.put(f"/api/v1/catalog/favorites/{second}", headers=headers).status_code == 204
    assert client.put(f"/api/v1/catalog/favorites/{second}", headers=headers).status_code == 204
    assert sorted(client.get("/api/v1/catalog/favorites", headers=headers).json()) == sorted([first, second])

    assert client.delete(f"/api/v1/catalog/favorites/{first}", headers=headers).status_code == 204
    assert client.delete(f"/api/v1/catalog/favorites/{first}", headers=headers).status_code == 204
    assert client.get("/api/v1/catalog/favorites", headers=headers).json() == [second]


def test_favorites_are_personal_and_need_a_real_piece(client: TestClient, user_token):
    item = client.get("/api/v1/catalog/furniture").json()[0]["id"]
    client.put(f"/api/v1/catalog/favorites/{item}", headers=auth(user_token))
    other = client.post(
        "/api/v1/auth/register", json={"full_name": "Otra", "email": "fav@example.com", "password": "secreta123"}
    ).json()["access_token"]
    assert client.get("/api/v1/catalog/favorites", headers=auth(other)).json() == []
    missing = client.put("/api/v1/catalog/favorites/999999", headers=auth(user_token))
    assert missing.status_code == 404 and "catálogo" in missing.json()["detail"]
