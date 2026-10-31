from app.core.settings import get_settings
from app.patterns.ai.ai_decorators import CachingImageEditor, LoggingImageEditor
from app.patterns.ai.ai_provider import DesignAdvisor, DesignSuggestions, ImageEditor
from app.patterns.ai.gemini_adapter import GeminiClient, GeminiDesignAdvisor, GeminiImageEditor
from app.patterns.ai.huggingface_adapter import HuggingFaceImageEditor
from app.patterns.ai.mock_adapter import MockDesignAdvisor, MockImageEditor
from app.patterns.singleton import SingletonMeta


# Singleton: one AI client per process, so the cache and HTTP settings are shared by every request.
class AIClient(metaclass=SingletonMeta):
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.image_editor: ImageEditor = CachingImageEditor(
            LoggingImageEditor(self._build_editor()), settings.ai_cache_size
        )

    def _gemini(self) -> GeminiClient:
        s = self.settings
        return GeminiClient(s.gemini_api_key, s.gemini_api_base_url, s.ai_timeout_seconds)

    def _build_editor(self) -> ImageEditor:
        s = self.settings
        match s.ai_image_provider:
            case "gemini":
                return GeminiImageEditor(self._gemini(), s.gemini_image_model)
            case "huggingface":
                return HuggingFaceImageEditor(
                    s.huggingface_api_token, s.huggingface_api_base_url, s.huggingface_image_model, s.ai_timeout_seconds
                )
            case _:
                return MockImageEditor()

    def advisor(self, fallback: DesignSuggestions) -> DesignAdvisor:
        if self.settings.ai_text_provider == "gemini":
            return GeminiDesignAdvisor(self._gemini(), self.settings.gemini_text_model)
        return MockDesignAdvisor(fallback)
