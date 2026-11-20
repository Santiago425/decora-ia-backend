from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderDescriptor:
    key: str
    label: str
    capabilities: tuple[str, ...]


# Every provider the AI layer can plug in; the active ones are chosen in the .env.
AI_PROVIDERS: tuple[ProviderDescriptor, ...] = (
    ProviderDescriptor("gemini", "Google Gemini", ("text", "image")),
    ProviderDescriptor("cloudflare", "Cloudflare Workers AI", ("image",)),
    ProviderDescriptor("huggingface", "Hugging Face", ("image",)),
    ProviderDescriptor("mock", "Modo demo", ("text", "image")),
)

STORAGE_PROVIDERS: tuple[ProviderDescriptor, ...] = (
    ProviderDescriptor("local", "Disco del servidor", ("storage",)),
    ProviderDescriptor("database", "Base de datos", ("storage",)),
)


def provider_keys(capability: str) -> set[str]:
    return {p.key for p in (*AI_PROVIDERS, *STORAGE_PROVIDERS) if capability in p.capabilities}
