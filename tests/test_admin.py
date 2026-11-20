import uuid

from fastapi.testclient import TestClient


def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", json={"email": "admin@test.app", "password": "DemoPass123", "role": "admin"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def user_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_admin_endpoints_reject_regular_users(client: TestClient, user_token: str):
    assert client.get("/api/v1/admin/stats", headers=user_headers(user_token)).status_code == 403
    response = client.patch("/api/v1/admin/styles/1", json={"name": "Hack"}, headers=user_headers(user_token))
    assert response.status_code == 403


def test_stats_cover_the_whole_platform(client: TestClient):
    response = client.get("/api/v1/admin/stats", headers=admin_headers(client))
    body = response.json()
    assert response.status_code == 200
    assert body["totals"]["users"] >= 2
    assert body["totals"]["projects"] >= 1
    assert len(body["daily"]) == body["days"]
    assert body["providers"]["text"] == "mock"


def test_users_search_and_pagination(client: TestClient):
    headers = admin_headers(client)
    body = client.get("/api/v1/admin/users", params={"search": "user@test"}, headers=headers).json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "user@test.app"
    assert body["items"][0]["project_count"] >= 1


def test_admin_cannot_remove_their_own_access(client: TestClient):
    headers = admin_headers(client)
    me = client.get("/api/v1/auth/me", headers=headers).json()
    response = client.patch(f"/api/v1/admin/users/{me['id']}", json={"is_active": False}, headers=headers)
    assert response.status_code == 422


def test_deactivated_user_cannot_log_in(client: TestClient):
    headers = admin_headers(client)
    email = f"temp-{uuid.uuid4().hex[:6]}@test.app"
    client.post("/api/v1/auth/register", json={"full_name": "Temp User", "email": email, "password": "TempPass123"})
    target = client.get("/api/v1/admin/users", params={"search": email}, headers=headers).json()["items"][0]

    updated = client.patch(f"/api/v1/admin/users/{target['id']}", json={"is_active": False}, headers=headers)
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "TempPass123"})

    assert updated.json()["is_active"] is False
    assert login.status_code in (401, 403)


def test_furniture_create_update_and_hide(client: TestClient, user_token: str):
    headers = admin_headers(client)
    category = client.get("/api/v1/catalog/furniture-categories").json()[0]["slug"]
    payload = {
        "category": category,
        "name": "Puff de prueba",
        "price": "150000",
        "width": 0.5,
        "depth": 0.5,
        "height": 0.4,
        "default_color": "#c4704f",
    }
    created = client.post("/api/v1/admin/furniture", json=payload, headers=headers)
    assert created.status_code == 201
    item_id = created.json()["id"]

    hidden = client.patch(
        f"/api/v1/admin/furniture/{item_id}", json={"is_active": False, "price": "99000"}, headers=headers
    )
    assert hidden.json()["is_active"] is False
    assert float(hidden.json()["price"]) == 99000

    public = client.get("/api/v1/catalog/furniture").json()
    assert all(item["id"] != item_id for item in public)


def test_furniture_rejects_unknown_category(client: TestClient):
    payload = {
        "category": "spaceships",
        "name": "Nave",
        "price": "1",
        "width": 1,
        "depth": 1,
        "height": 1,
        "default_color": "#000000",
    }
    response = client.post("/api/v1/admin/furniture", json=payload, headers=admin_headers(client))
    assert response.status_code == 422


def test_style_update(client: TestClient):
    headers = admin_headers(client)
    style = client.get("/api/v1/admin/styles", headers=headers).json()[0]
    response = client.patch(f"/api/v1/admin/styles/{style['id']}", json={"lighting_intensity": 1.2}, headers=headers)
    assert response.json()["lighting_intensity"] == 1.2


def test_reports_download_as_csv(client: TestClient):
    headers = admin_headers(client)
    users = client.get("/api/v1/admin/reports/usuarios", headers=headers)
    projects = client.get("/api/v1/admin/reports/proyectos", headers=headers)
    assert users.headers["content-type"].startswith("text/csv")
    assert "Correo" in users.text and "user@test.app" in users.text
    assert "Presupuesto" in projects.text
    assert client.get("/api/v1/admin/reports/secret", headers=headers).status_code == 404


def test_reports_share_formats_through_the_bridge(client: TestClient):
    headers = admin_headers(client)
    response = client.get("/api/v1/admin/reports/usuarios?format=json", headers=headers)
    assert response.headers["content-type"].startswith("application/json")
    assert 'filename="habita-usuarios-' in response.headers["content-disposition"]
    assert response.headers["content-disposition"].endswith('.json"')
    rows = response.json()
    assert any(row["Correo"] == "user@test.app" for row in rows)
    assert client.get("/api/v1/admin/reports/proyectos?format=json", headers=headers).json()[0].keys() >= {"Proyecto"}
    assert client.get("/api/v1/admin/reports/usuarios?format=pdf", headers=headers).status_code == 422


def test_meta_info_lists_demo_accounts(client: TestClient, user_token: str):
    body = client.get("/api/v1/meta/info", headers=user_headers(user_token)).json()
    assert {account["role"] for account in body["demo_accounts"]} == {"user", "admin"}
    assert body["assistant_name"] == "Lumi"


def test_users_filter_by_role_and_status(client: TestClient):
    headers = admin_headers(client)
    admins = client.get("/api/v1/admin/users", params={"role": "admin"}, headers=headers).json()
    assert admins["total"] >= 1
    assert all(user["role"] == "admin" for user in admins["items"])

    inactive = client.get("/api/v1/admin/users", params={"active": "false"}, headers=headers).json()
    assert all(user["is_active"] is False for user in inactive["items"])

    bad = client.get("/api/v1/admin/users", params={"role": "owner"}, headers=headers)
    assert bad.status_code == 422


def test_furniture_list_is_paginated_and_filtered(client: TestClient):
    headers = admin_headers(client)
    first = client.get("/api/v1/admin/furniture", headers=headers).json()
    assert first["page"] == 1
    assert first["total"] >= len(first["items"])
    assert len(first["items"]) <= first["page_size"]

    category = first["items"][0]["category"]["slug"]
    by_category = client.get("/api/v1/admin/furniture", params={"category": category}, headers=headers).json()
    assert by_category["total"] >= 1
    assert all(item["category"]["slug"] == category for item in by_category["items"])

    name = first["items"][0]["name"]
    found = client.get("/api/v1/admin/furniture", params={"search": name[:4].upper()}, headers=headers).json()
    assert any(item["name"] == name for item in found["items"])

    hidden = client.get("/api/v1/admin/furniture", params={"active": "false"}, headers=headers).json()
    assert all(item["is_active"] is False for item in hidden["items"])

    empty = client.get("/api/v1/admin/furniture", params={"page": 999}, headers=headers).json()
    assert empty["items"] == []
    assert empty["total"] == first["total"]


def test_room_type_cover_can_be_changed_from_the_admin(client: TestClient, user_token: str):
    headers = admin_headers(client)
    room_type = client.get("/api/v1/admin/room-types", headers=headers).json()[0]
    assert room_type["cover_image_url"]
    url = "https://images.example.com/new-cover.jpg"
    response = client.patch(
        f"/api/v1/admin/room-types/{room_type['id']}", json={"cover_image_url": url}, headers=headers
    )
    assert response.json()["cover_image_url"] == url
    public = next(r for r in client.get("/api/v1/catalog/room-types").json() if r["id"] == room_type["id"])
    assert public["cover_image_url"] == url
    blocked = client.patch(
        f"/api/v1/admin/room-types/{room_type['id']}", json={"name": "Hack"}, headers=user_headers(user_token)
    )
    assert blocked.status_code == 403
