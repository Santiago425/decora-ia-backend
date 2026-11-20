from app.core.settings import get_settings
from app.patterns.ai.ai_decorators import CachingImageEditor, FallbackImageEditor, LoggingImageEditor
from app.patterns.ai.ai_provider import DesignAdvisor, DesignSuggestions, ImageEditor
from app.patterns.ai.mock_adapter import MockImageEditor
from app.patterns.ai.provider_factories import factory_for
from app.patterns.singleton import SingletonMeta


# Singleton: one AI client per process, so the cache and HTTP settings are shared by every request.
class AIClient(metaclass=SingletonMeta):
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        editor: ImageEditor = LoggingImageEditor(
            factory_for(settings.ai_image_provider, settings).create_image_editor()
        )
        if settings.ai_image_provider != "mock" and settings.ai_image_fallback == "mock":
            editor = FallbackImageEditor(editor, MockImageEditor())
        self.image_editor: ImageEditor = CachingImageEditor(editor, settings.ai_cache_size)

    def advisor(self, fallback: DesignSuggestions) -> DesignAdvisor:
        return factory_for(self.settings.ai_text_provider, self.settings).create_design_advisor(fallback)
