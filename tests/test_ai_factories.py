import pytest

from app.core.settings import Settings
from app.patterns.ai.ai_provider import DesignSuggestions
from app.patterns.ai.cloudflare_adapter import CloudflareImageEditor
from app.patterns.ai.gemini_adapter import GeminiDesignAdvisor, GeminiImageEditor
from app.patterns.ai.huggingface_adapter import HuggingFaceImageEditor
from app.patterns.ai.mock_adapter import MockDesignAdvisor, MockImageEditor
from app.patterns.ai.provider_factories import FACTORIES, factory_for

SETTINGS = Settings(
    gemini_api_key="key",
    cloudflare_account_id="account",
    cloudflare_api_token="token",
    huggingface_api_token="token",
    huggingface_image_model="model",
)
FALLBACK = DesignSuggestions(summary="local")


@pytest.mark.parametrize(
    ("provider", "editor", "advisor"),
    [
        ("gemini", GeminiImageEditor, GeminiDesignAdvisor),
        ("cloudflare", CloudflareImageEditor, MockDesignAdvisor),
        ("huggingface", HuggingFaceImageEditor, MockDesignAdvisor),
        ("mock", MockImageEditor, MockDesignAdvisor),
    ],
)
def test_each_factory_builds_its_own_family(provider, editor, advisor):
    factory = factory_for(provider, SETTINGS)
    assert isinstance(factory.create_image_editor(), editor)
    assert isinstance(factory.create_design_advisor(FALLBACK), advisor)


def test_unknown_provider_falls_back_to_the_demo_family():
    assert isinstance(factory_for("nope", SETTINGS).create_image_editor(), MockImageEditor)


def test_every_catalog_provider_has_a_factory():
    from app.patterns.ai.provider_catalog import AI_PROVIDERS

    assert {p.key for p in AI_PROVIDERS} == set(FACTORIES)
