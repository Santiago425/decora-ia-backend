from fastapi.testclient import TestClient


def test_register_creates_a_user_account(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={"full_name": "  Ana   Pérez ", "email": "Ana@Example.com", "password": "secreta123"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["full_name"] == "Ana Pérez"
    assert body["user"]["email"] == "ana@example.com"
    assert body["user"]["role"] == "user"
    assert body["access_token"]
    assert "password_hash" not in body["user"]


def test_register_rejects_duplicate_email(client: TestClient):
    payload = {"full_name": "Luis", "email": "luis@example.com", "password": "secreta123"}
    client.post("/api/v1/auth/register", json=payload)
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409


def test_register_rejects_weak_password(client: TestClient):
    response = client.post(
        "/api/v1/auth/register", json={"full_name": "Eva", "email": "eva@example.com", "password": "solotexto"}
    )
    assert response.status_code == 422
    assert "contraseña" in response.json()["fields"]


def test_login_with_demo_user(client: TestClient):
    response = client.post("/api/v1/auth/login", json={"email": "user@test.app", "password": "DemoPass123"})
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "user"


def test_login_with_demo_admin_requires_admin_role(client: TestClient):
    credentials = {"email": "admin@test.app", "password": "DemoPass123"}
    assert client.post("/api/v1/auth/login", json=credentials).status_code == 403
    response = client.post("/api/v1/auth/login", json=credentials | {"role": "admin"})
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "admin"


def test_user_cannot_enter_as_admin(client: TestClient):
    response = client.post(
        "/api/v1/auth/login", json={"email": "user@test.app", "password": "DemoPass123", "role": "admin"}
    )
    assert response.status_code == 403


def test_login_rejects_wrong_password_with_generic_message(client: TestClient):
    wrong_password = client.post("/api/v1/auth/login", json={"email": "user@test.app", "password": "nope1234"})
    unknown_email = client.post("/api/v1/auth/login", json={"email": "ghost@test.app", "password": "nope1234"})
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_me_requires_a_valid_token(client: TestClient, user_token: str):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid"}).status_code == 401
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {user_token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "user@test.app"
