from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str
    app_env: str = "development"
    api_prefix: str = "/api/v1"

    database_url: str
    database_echo: bool = False

    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 120

    login_rate_limit: str = "10/minute"
    register_rate_limit: str = "5/minute"

    seed_on_startup: bool = False
    seed_demo_projects: bool = False
    demo_password: str = Field(min_length=8)
    demo_user_email: str
    demo_user_name: str
    demo_admin_email: str
    demo_admin_name: str

    currency_code: str = "COP"

    storage_provider: str = "local"
    media_dir: str = "media"
    media_url_path: str = "/media"
    max_upload_mb: float = 8
    min_image_side: int = 256
    max_image_side: int = 1536

    ai_text_provider: str = "mock"
    ai_image_provider: str = "mock"
    ai_timeout_seconds: float = 90
    ai_cache_size: int = 32
    redesign_rate_limit: str = "6/minute"

    gemini_api_key: str = ""
    gemini_api_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_text_model: str = "gemini-3.5-flash-lite"
    gemini_image_model: str = "gemini-2.5-flash-image"

    huggingface_api_token: str = ""
    huggingface_api_base_url: str = "https://router.huggingface.co/hf-inference/models"
    huggingface_image_model: str = ""

    budget_economic_max: float = 3_000_000
    budget_standard_max: float = 12_000_000

    room_default_width: float = 5.0
    room_default_length: float = 4.0
    room_default_height: float = 2.7
    scene_max_nodes: int = 150
    scene_versions_limit: int = 20

    assistant_name: str = "Lumi"
    assistant_rate_limit: str = "20/minute"
    assistant_history_limit: int = 40
    assistant_context_messages: int = 6

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix):]
        return value

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


# Singleton: the configuration is read from the environment once and shared by the whole app.
@lru_cache
def get_settings() -> Settings:
    return Settings()
