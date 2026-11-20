from abc import ABC, abstractmethod

from app.core.settings import Settings
from app.patterns.ai.ai_provider import DesignAdvisor, DesignSuggestions, ImageEditor
from app.patterns.ai.cloudflare_adapter import CloudflareImageEditor
from app.patterns.ai.gemini_adapter import GeminiClient, GeminiDesignAdvisor, GeminiImageEditor
from app.patterns.ai.huggingface_adapter import HuggingFaceImageEditor
from app.patterns.ai.mock_adapter import MockDesignAdvisor, MockImageEditor


# Abstract Factory: each provider builds its own family of AI products (image editor and design advisor)
# configured from the same settings; a provider without text support falls back to the local advisor.
class AIProviderFactory(ABC):
    key: str

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @abstractmethod
    def create_image_editor(self) -> ImageEditor: ...

    def create_design_advisor(self, fallback: DesignSuggestions) -> DesignAdvisor:
        return MockDesignAdvisor(fallback)


class GeminiFactory(AIProviderFactory):
    key = "gemini"

    def _client(self) -> GeminiClient:
        s = self.settings
        return GeminiClient(s.gemini_api_key, s.gemini_api_base_url, s.ai_timeout_seconds)

    def create_image_editor(self) -> ImageEditor:
        return GeminiImageEditor(self._client(), self.settings.gemini_image_model)

    def create_design_advisor(self, fallback: DesignSuggestions) -> DesignAdvisor:
        return GeminiDesignAdvisor(self._client(), self.settings.gemini_text_model)


class CloudflareFactory(AIProviderFactory):
    key = "cloudflare"

    def create_image_editor(self) -> ImageEditor:
        s = self.settings
        return CloudflareImageEditor(
            s.cloudflare_account_id,
            s.cloudflare_api_token,
            s.cloudflare_api_base_url,
            s.cloudflare_image_model,
            s.cloudflare_image_strength,
            s.cloudflare_image_side,
            s.ai_timeout_seconds,
        )


class HuggingFaceFactory(AIProviderFactory):
    key = "huggingface"

    def create_image_editor(self) -> ImageEditor:
        s = self.settings
        return HuggingFaceImageEditor(
            s.huggingface_api_token, s.huggingface_provider, s.huggingface_image_model, s.ai_timeout_seconds
        )


class MockFactory(AIProviderFactory):
    key = "mock"

    def create_image_editor(self) -> ImageEditor:
        return MockImageEditor()


FACTORIES: dict[str, type[AIProviderFactory]] = {
    factory.key: factory for factory in (GeminiFactory, CloudflareFactory, HuggingFaceFactory, MockFactory)
}


def factory_for(provider: str, settings: Settings) -> AIProviderFactory:
    return FACTORIES.get(provider, MockFactory)(settings)
