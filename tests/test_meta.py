import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.settings import Settings, get_settings
from app.seed import run_seed


def test_public_meta_needs_no_session(client: TestClient):
    response = client.get("/api/v1/meta/public")
    assert response.status_code == 200
    body = response.json()
    assert body["assistant_name"] == "Lumi"
    assert {account["role"] for account in body["demo_accounts"]} == {"user", "admin"}
    assert body["providers"] == {"text": "mock", "image": "mock", "image_fallback": "none", "storage": "database"}


def test_public_meta_lists_every_ai_provider_with_the_active_ones(client: TestClient):
    providers = {p["key"]: p for p in client.get("/api/v1/meta/public").json()["available_providers"]}
    assert {"gemini", "cloudflare", "huggingface", "mock", "database"} <= providers.keys()
    assert providers["cloudflare"]["label"] == "Cloudflare Workers AI"
    assert providers["mock"]["active_for"] == ["text", "image"]
    assert providers["database"]["active_for"] == ["storage"]


def test_public_meta_hides_demo_accounts_when_disabled(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(get_settings(), "show_demo_accounts", False)
    assert client.get("/api/v1/meta/public").json()["demo_accounts"] == []


def test_demo_accounts_carry_the_greeting_from_the_settings(client: TestClient):
    accounts = client.get("/api/v1/meta/public").json()["demo_accounts"]
    assert {account["greeting"] for account in accounts} == {"Welcome, dear tester"}


def test_seed_renames_the_demo_account_from_the_settings(
    client: TestClient, user_token: str, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(get_settings(), "demo_user_name", "Tester")
    run_seed()
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {user_token}"}).json()
    monkeypatch.undo()
    run_seed()
    assert me["full_name"] == "Tester"


def test_production_refuses_the_example_jwt_secret(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "change-me-with-a-long-random-string-of-64-chars")
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings()


def test_production_accepts_a_real_secret(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "q8Zr2mVt7xLp4NsW9cHk3JdF6bYg1TaE5uRo0iQz")
    assert Settings().is_production


def test_unknown_ai_provider_is_rejected(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AI_IMAGE_PROVIDER", "dalle")
    with pytest.raises(ValidationError):
        Settings()


def test_missing_provider_credentials_are_reported(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AI_IMAGE_PROVIDER", "cloudflare")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "")
    assert Settings().provider_problems() == [
        "AI_IMAGE_PROVIDER=cloudflare needs CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN"
    ]
