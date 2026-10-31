import base64

import httpx

from app.patterns.ai.ai_provider import AIError, ImageData, ImageEditor


# Adapter: wraps the Hugging Face image-to-image inference API behind the ImageEditor interface.
class HuggingFaceImageEditor(ImageEditor):
    name = "huggingface"

    def __init__(self, token: str, base_url: str, model: str, timeout: float) -> None:
        if not token or not model:
            raise AIError("Falta configurar Hugging Face (HUGGINGFACE_API_TOKEN y HUGGINGFACE_IMAGE_MODEL)")
        self.url = f"{base_url.rstrip('/')}/{model}"
        self.token = token
        self.timeout = timeout

    def edit(self, image: ImageData, prompt: str) -> ImageData:
        try:
            response = httpx.post(
                self.url,
                headers={"Authorization": f"Bearer {self.token}", "Accept": "image/png"},
                json={"inputs": base64.b64encode(image.data).decode(), "parameters": {"prompt": prompt}},
                timeout=self.timeout,
            )
        except httpx.HTTPError:
            raise AIError("El modelo de imágenes no respondió. Inténtalo de nuevo") from None
        if response.status_code == 503:
            raise AIError("El modelo de imágenes se está encendiendo. Inténtalo en un minuto")
        if response.status_code >= 400 or not response.headers.get("content-type", "").startswith("image/"):
            raise AIError("El modelo de imágenes no pudo procesar la foto. Inténtalo de nuevo")
        return ImageData(response.content, response.headers["content-type"].split(";")[0])
