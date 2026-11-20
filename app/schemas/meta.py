from pydantic import BaseModel

from app.schemas.admin import ProviderInfo


class DemoAccount(BaseModel):
    role: str
    name: str
    email: str
    password: str
    greeting: str = ""


class ProviderOption(BaseModel):
    key: str
    label: str
    capabilities: list[str]
    active_for: list[str]


class PublicMeta(BaseModel):
    app_name: str
    assistant_name: str
    environment: str
    currency_code: str
    providers: ProviderInfo
    available_providers: list[ProviderOption]
    demo_accounts: list[DemoAccount]


class AppInfo(PublicMeta):
    api_prefix: str
