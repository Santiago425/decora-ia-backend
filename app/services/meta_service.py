from app.core.settings import Settings
from app.patterns.ai.provider_catalog import AI_PROVIDERS, STORAGE_PROVIDERS
from app.schemas.admin import ProviderInfo
from app.schemas.meta import AppInfo, DemoAccount, ProviderOption, PublicMeta


def active_providers(settings: Settings) -> ProviderInfo:
    fallback = settings.ai_image_fallback if settings.ai_image_provider != "mock" else "none"
    return ProviderInfo(
        text=settings.ai_text_provider,
        image=settings.ai_image_provider,
        image_fallback=fallback,
        storage=settings.storage_provider,
    )


def _available(settings: Settings) -> list[ProviderOption]:
    active = active_providers(settings)
    roles = {"text": active.text, "image": active.image, "storage": active.storage}
    return [
        ProviderOption(
            key=provider.key,
            label=provider.label,
            capabilities=list(provider.capabilities),
            active_for=[role for role, key in roles.items() if key == provider.key],
        )
        for provider in (*AI_PROVIDERS, *STORAGE_PROVIDERS)
    ]


def _demo_accounts(settings: Settings) -> list[DemoAccount]:
    if not settings.show_demo_accounts:
        return []
    return [
        DemoAccount(
            role="user",
            name=settings.demo_user_name,
            email=settings.demo_user_email,
            password=settings.demo_password,
            greeting=settings.demo_greeting,
        ),
        DemoAccount(
            role="admin",
            name=settings.demo_admin_name,
            email=settings.demo_admin_email,
            password=settings.demo_password,
            greeting=settings.demo_greeting,
        ),
    ]


def public_meta(settings: Settings) -> PublicMeta:
    return PublicMeta(
        app_name=settings.app_name,
        assistant_name=settings.assistant_name,
        environment=settings.app_env,
        currency_code=settings.currency_code,
        providers=active_providers(settings),
        available_providers=_available(settings),
        demo_accounts=_demo_accounts(settings),
    )


def app_info(settings: Settings) -> AppInfo:
    return AppInfo(**public_meta(settings).model_dump(), api_prefix=settings.api_prefix)
