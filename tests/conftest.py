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
        "STORAGE_PROVIDER": "database",
        "AI_TEXT_PROVIDER": "mock",
        "AI_IMAGE_PROVIDER": "mock",
        "REDESIGN_RATE_LIMIT": "1000/minute",
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


def make_photo(size=(800, 600), fmt="JPEG") -> bytes:
    import io

    from PIL import Image, ImageDraw

    image = Image.new("RGB", size, (200, 190, 175))
    draw = ImageDraw.Draw(image)
    for x in range(0, size[0], 40):
        draw.rectangle([x, size[1] // 2, x + 20, size[1]], fill=(90 + x % 120, 70, 60))
    draw.rectangle([size[0] // 3, size[1] // 10, size[0] // 2, size[1] // 3], fill=(240, 240, 255))
    buffer = io.BytesIO()
    image.save(buffer, fmt)
    return buffer.getvalue()


@pytest.fixture
def photo() -> bytes:
    return make_photo()
