from fastapi.testclient import TestClient

from app.core.database import Database
from app.core.security import PasswordHasher, TokenService
from app.core.settings import Settings, get_settings


def test_settings_is_a_singleton():
    assert get_settings() is get_settings()


def test_database_is_a_singleton():
    assert Database() is Database()


def test_settings_convert_postgres_urls_to_psycopg():
    converted = Settings.use_psycopg_driver("postgresql://u:p@host/db?sslmode=require")
    assert converted.startswith("postgresql+psycopg://")


def test_password_hasher_never_stores_plain_text():
    hashed = PasswordHasher.hash("secreta123")
    assert hashed != "secreta123"
    assert PasswordHasher.verify("secreta123", hashed)
    assert not PasswordHasher.verify("otra123", hashed)


def test_token_contains_subject_and_role():
    token, expires_in = TokenService.create("abc", "admin")
    payload = TokenService.decode(token)
    assert payload["sub"] == "abc" and payload["role"] == "admin"
    assert expires_in == get_settings().jwt_expire_minutes * 60


def test_hello_and_health(client: TestClient):
    assert client.get("/api/v1/hello").json() == {"message": "Hello World from Habita"}
    health = client.get("/api/v1/health").json()
    assert health["database"] == "up"


def test_cors_allows_configured_origin_only(client: TestClient):
    allowed = client.options(
        "/api/v1/hello", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"}
    )
    blocked = client.options(
        "/api/v1/hello", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"}
    )
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in blocked.headers
