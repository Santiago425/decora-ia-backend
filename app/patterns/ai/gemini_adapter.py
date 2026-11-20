import base64
import json
import re
import time
from typing import ClassVar

import httpx
from pydantic import ValidationError

from app.patterns.ai.ai_provider import (
    AIError,
    DesignAdvisor,
    DesignSuggestions,
    ImageData,
    ImageEditor,
    StyleDescriber,
    StyleDescription,
)

HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
QUOTA_MESSAGE = "La IA alcanzó su límite por ahora. Espera un momento e inténtalo de nuevo"
UNAVAILABLE_MESSAGE = "La IA no está disponible en este momento. Inténtalo de nuevo en unos segundos"
STYLE_PROMPT = (
    "You are an interior designer. Look at this inspiration photo and describe its decoration style so an image "
    "model can apply it to another room. Ignore people, text, logos and brands. Answer only with JSON shaped as "
    '{"name": str, "summary": str, "prompt": str, "colors": ["#RRGGBB"]}: "name" is the style name in Spanish '
    '(max 4 words), "summary" is one or two short sentences in Spanish for the user, "prompt" is an English brief '
    '(max 90 words) with the style, furniture shapes, materials, textures, lighting and mood, and "colors" has '
    "the 3 to 5 main colors of the photo."
)


class GeminiClient:
    retry_statuses: ClassVar[frozenset[int]] = frozenset({500, 503})
    max_attempts = 3

    def __init__(self, api_key: str, base_url: str, timeout: float) -> None:
        if not api_key:
            raise AIError("Falta configurar la clave de Gemini (GEMINI_API_KEY)")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(self, model: str, parts: list[dict], generation_config: dict) -> list[dict]:
        response = self._post(
            model, {"contents": [{"role": "user", "parts": parts}], "generationConfig": generation_config}
        )
        if response.status_code == 429:
            raise AIError(QUOTA_MESSAGE)
        if response.status_code >= 400:
            raise AIError(UNAVAILABLE_MESSAGE)
        candidates = response.json().get("candidates") or []
        if not candidates:
            raise AIError("La IA no pudo procesar esta foto. Prueba con otra imagen")
        return candidates[0].get("content", {}).get("parts", [])

    def _post(self, model: str, body: dict) -> httpx.Response:
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = httpx.post(
                    f"{self.base_url}/models/{model}:generateContent",
                    headers={"x-goog-api-key": self.api_key},
                    json=body,
                    timeout=self.timeout,
                )
            except httpx.HTTPError:
                if attempt == self.max_attempts:
                    raise AIError(UNAVAILABLE_MESSAGE) from None
                continue
            if response.status_code not in self.retry_statuses or attempt == self.max_attempts:
                return response
            time.sleep(attempt)
        raise AIError(UNAVAILABLE_MESSAGE)

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


class GeminiStyleDescriber(StyleDescriber):
    name = "gemini"

    def __init__(self, client: GeminiClient, model: str) -> None:
        self.client = client
        self.model = model

    def describe(self, image: ImageData) -> StyleDescription:
        parts = self.client.generate(
            self.model,
            [self.client.inline(image), {"text": STYLE_PROMPT}],
            {"responseMimeType": "application/json", "temperature": 0.4},
        )
        text = "".join(part.get("text", "") for part in parts)
        try:
            data = json.loads(text)
            data["colors"] = [c for c in data.get("colors", []) if isinstance(c, str) and HEX_COLOR.match(c)][:5]
            return StyleDescription.model_validate(data)
        except (json.JSONDecodeError, ValidationError, AttributeError, TypeError):
            raise AIError("La IA no pudo leer el estilo de esa foto. Prueba con otra imagen") from None
