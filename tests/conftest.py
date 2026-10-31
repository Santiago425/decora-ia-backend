import os
import tempfile
from pathlib import Path

_db_file = Path(tempfile.mkdtemp()) / "test.db"
os.environ.update(
    {
        "APP_NAME": "Habita",
        "APP_ENV": "test",
        "DATABASE_URL": f"sqlite:///{_db_file}",
        "CORS_ORIGINS": "http://localhost:5173",
        "JWT_SECRET": "test-secret-that-is-long-enough-for-hs256-signing",
        "LOGIN_RATE_LIMIT": "1000/minute",
        "REGISTER_RATE_LIMIT": "1000/minute",
        "SEED_ON_STARTUP": "false",
        "SEED_DEMO_PROJECTS": "true",
        "DEMO_PASSWORD": "DemoPass123",
        "DEMO_USER_EMAIL": "user@test.app",
        "DEMO_USER_NAME": "Test User",
        "DEMO_ADMIN_EMAIL": "admin@test.app",
        "DEMO_ADMIN_NAME": "Test Admin",
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Database  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Base  # noqa: E402
from app.seed import run_seed  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def database():
    Base.metadata.create_all(Database().engine)
    run_seed()
    yield
    Base.metadata.drop_all(Database().engine)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def user_token(client: TestClient) -> str:
    response = client.post("/api/v1/auth/login", json={"email": "user@test.app", "password": "DemoPass123"})
    return response.json()["access_token"]
