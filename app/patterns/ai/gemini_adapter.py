import base64
import json

import httpx
from pydantic import ValidationError

from app.patterns.ai.ai_provider import AIError, DesignAdvisor, DesignSuggestions, ImageData, ImageEditor

QUOTA_MESSAGE = "La IA alcanzó su límite por ahora. Espera un momento e inténtalo de nuevo"
UNAVAILABLE_MESSAGE = "La IA no está disponible en este momento. Inténtalo de nuevo en unos segundos"


class GeminiClient:
    def __init__(self, api_key: str, base_url: str, timeout: float) -> None:
        if not api_key:
            raise AIError("Falta configurar la clave de Gemini (GEMINI_API_KEY)")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(self, model: str, parts: list[dict], generation_config: dict) -> list[dict]:
        try:
            response = httpx.post(
                f"{self.base_url}/models/{model}:generateContent",
                headers={"x-goog-api-key": self.api_key},
                json={"contents": [{"role": "user", "parts": parts}], "generationConfig": generation_config},
                timeout=self.timeout,
            )
        except httpx.HTTPError:
            raise AIError(UNAVAILABLE_MESSAGE) from None
        if response.status_code == 429:
            raise AIError(QUOTA_MESSAGE)
        if response.status_code >= 400:
            raise AIError(UNAVAILABLE_MESSAGE)
        candidates = response.json().get("candidates") or []
        if not candidates:
            raise AIError("La IA no pudo procesar esta foto. Prueba con otra imagen")
        return candidates[0].get("content", {}).get("parts", [])

    @staticmethod
    def inline(image: ImageData) -> dict:
        return {"inline_data": {"mime_type": image.content_type, "data": base64.b64encode(image.data).decode()}}


# Adapter: translates Gemini's REST format into the ImageEditor and DesignAdvisor interfaces.
class GeminiImageEditor(ImageEditor):
    name = "gemini"

    def __init__(self, client: GeminiClient, model: str) -> None:
        self.client = client
        self.model = model

    def edit(self, image: ImageData, prompt: str) -> ImageData:
        parts = self.client.generate(
            self.model, [self.client.inline(image), {"text": prompt}], {"responseModalities": ["TEXT", "IMAGE"]}
        )
        for part in parts:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                content_type = inline.get("mimeType") or inline.get("mime_type") or "image/png"
                return ImageData(base64.b64decode(inline["data"]), content_type)
        raise AIError("La IA no devolvió una imagen esta vez. Inténtalo de nuevo")


class GeminiDesignAdvisor(DesignAdvisor):
    name = "gemini"

    def __init__(self, client: GeminiClient, model: str) -> None:
        self.client = client
        self.model = model

    def suggest(self, image: ImageData, prompt: str) -> DesignSuggestions:
        parts = self.client.generate(
            self.model,
            [self.client.inline(image), {"text": prompt}],
            {"responseMimeType": "application/json", "temperature": 0.6},
        )
        text = "".join(part.get("text", "") for part in parts)
        try:
            return DesignSuggestions.model_validate(json.loads(text))
        except (json.JSONDecodeError, ValidationError):
            raise AIError("La IA respondió en un formato inesperado. Inténtalo de nuevo") from None
