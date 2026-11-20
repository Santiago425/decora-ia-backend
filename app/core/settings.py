import logging
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

logger = logging.getLogger("habita.settings")

INSECURE_SECRET_PREFIXES = ("change-me", "changeme", "secret", "test-secret")


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

    storage_provider: Literal["local", "database"] = "local"
    media_dir: str = "media"
    media_url_path: str = "/media"
    max_upload_mb: float = 8
    min_image_side: int = 256
    max_image_side: int = 1536

    ai_text_provider: Literal["gemini", "mock"] = "mock"
    ai_image_provider: Literal["gemini", "cloudflare", "huggingface", "mock"] = "mock"
    # "none" shows the user a clear error when the image provider fails; "mock" returns a tinted copy (demo only).
    ai_image_fallback: Literal["mock", "none"] = "none"
    ai_timeout_seconds: float = 90
    # Extra attempts when the image provider is busy or times out.
    ai_retry_attempts: int = Field(default=1, ge=0, le=3)
    ai_retry_delay_seconds: float = Field(default=2, ge=0)
    # Average pixel difference (0-255) below which a generated image counts as an unchanged copy of the photo.
    ai_min_change: float = Field(default=2.0, ge=0)
    ai_cache_size: int = 32
    redesign_rate_limit: str = "6/minute"

    # Public endpoints and model names have working defaults on purpose; override them from the .env.
    gemini_api_key: str = ""
    gemini_api_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_text_model: str = "gemini-3.5-flash-lite"
    gemini_image_model: str = "gemini-2.5-flash-image"

    huggingface_api_token: str = ""
    huggingface_provider: str = "auto"
    huggingface_image_model: str = "black-forest-labs/FLUX.1-Kontext-dev"

    cloudflare_account_id: str = ""
    cloudflare_api_token: str = ""
    cloudflare_api_base_url: str = "https://api.cloudflare.com/client/v4"
    cloudflare_image_model: str = "@cf/runwayml/stable-diffusion-v1-5-img2img"
    cloudflare_image_strength: float = 0.6
    cloudflare_image_side: int = 768

    budget_economic_max: float = 3_000_000
    budget_standard_max: float = 12_000_000
    shopping_budget_warning_ratio: float = Field(default=0.9, gt=0, le=1)
    shopping_max_purchased: int = 300

    room_default_width: float = 5.0
    room_default_length: float = 4.0
    room_default_height: float = 2.7
    scene_max_nodes: int = 150
    scene_versions_limit: int = 20

    assistant_name: str = "Lumi"
    assistant_rate_limit: str = "20/minute"
    assistant_history_limit: int = 40
    assistant_context_messages: int = 6

    admin_page_size: int = 20
    admin_stats_days: int = 14
    show_demo_accounts: bool = True

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
                return "postgresql+psycopg://" + value[len(prefix) :]
        return value

    @model_validator(mode="after")
    def check_safe_configuration(self) -> "Settings":
        if self.is_production and self.jwt_secret.lower().startswith(INSECURE_SECRET_PREFIXES):
            raise ValueError("JWT_SECRET is the example value: set a long random secret before running in production")
        for problem in self.provider_problems():
            logger.warning("settings %s", problem)
        return self

    def provider_problems(self) -> list[str]:
        required = {
            "gemini": {"GEMINI_API_KEY": self.gemini_api_key},
            "cloudflare": {
                "CLOUDFLARE_ACCOUNT_ID": self.cloudflare_account_id,
                "CLOUDFLARE_API_TOKEN": self.cloudflare_api_token,
            },
            "huggingface": {"HUGGINGFACE_API_TOKEN": self.huggingface_api_token},
        }
        problems = []
        for role, provider in (
            ("AI_TEXT_PROVIDER", self.ai_text_provider),
            ("AI_IMAGE_PROVIDER", self.ai_image_provider),
        ):
            missing = [name for name, value in required.get(provider, {}).items() if not value]
            if missing:
                problems.append(f"{role}={provider} needs {', '.join(missing)}")
        return problems

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


# Singleton: the configuration is read from the environment once and shared by the whole app.
@lru_cache
def get_settings() -> Settings:
    return Settings()
