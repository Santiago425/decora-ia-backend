import base64
import io

import httpx
from PIL import Image, ImageOps

from app.patterns.ai.ai_provider import AIError, ImageData, ImageEditor


# Adapter: wraps Cloudflare Workers AI (Stable Diffusion img2img) behind the ImageEditor interface.
class CloudflareImageEditor(ImageEditor):
    name = "cloudflare"

    def __init__(
        self, account_id: str, token: str, base_url: str, model: str, strength: float, side: int, timeout: float
    ) -> None:
        if not account_id or not token:
            raise AIError("Falta configurar Cloudflare (CLOUDFLARE_ACCOUNT_ID y CLOUDFLARE_API_TOKEN)")
        self.url = f"{base_url.rstrip('/')}/accounts/{account_id}/ai/run/{model}"
        self.token = token
        self.strength = strength
        self.side = side
        self.timeout = timeout

    def _prepare(self, image: ImageData) -> bytes:
        photo = ImageOps.exif_transpose(Image.open(io.BytesIO(image.data))).convert("RGB")
        photo.thumbnail((self.side, self.side))
        photo = photo.resize((photo.width // 8 * 8, photo.height // 8 * 8))
        buffer = io.BytesIO()
        photo.save(buffer, "PNG")
        return buffer.getvalue()

    def edit(self, image: ImageData, prompt: str) -> ImageData:
        payload = {
            "prompt": prompt,
            "image_b64": base64.b64encode(self._prepare(image)).decode(),
            "strength": self.strength,
            "num_steps": 20,
        }
        try:
            response = httpx.post(
                self.url, headers={"Authorization": f"Bearer {self.token}"}, json=payload, timeout=self.timeout
            )
        except httpx.HTTPError:
            raise AIError("El modelo de imágenes no respondió. Inténtalo de nuevo") from None
        content_type = response.headers.get("content-type", "")
        if response.status_code >= 400 or not content_type.startswith("image/"):
            raise AIError(f"El modelo de imágenes no pudo procesar la foto (Cloudflare {response.status_code})")
        return ImageData(response.content, content_type.split(";")[0])
