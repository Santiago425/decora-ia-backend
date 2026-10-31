from pydantic import BaseModel

from app.schemas.admin import ProviderInfo


class DemoAccount(BaseModel):
    role: str
    name: str
    email: str
    password: str


class AppInfo(BaseModel):
    app_name: str
    assistant_name: str
    environment: str
    api_prefix: str
    providers: ProviderInfo
    demo_accounts: list[DemoAccount]
