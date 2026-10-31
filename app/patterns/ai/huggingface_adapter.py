import io
import logging

from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError, InferenceTimeoutError

from app.patterns.ai.ai_provider import AIError, ImageData, ImageEditor

logger = logging.getLogger("habita.ai")


# Adapter: wraps Hugging Face Inference Providers (image-to-image) behind the ImageEditor interface.
class HuggingFaceImageEditor(ImageEditor):
    name = "huggingface"

    def __init__(self, token: str, provider: str, model: str, timeout: float) -> None:
        if not token or not model:
            raise AIError("Falta configurar Hugging Face (HUGGINGFACE_API_TOKEN y HUGGINGFACE_IMAGE_MODEL)")
        self.model = model
        self.client = InferenceClient(provider=provider or "auto", api_key=token, timeout=timeout)

    def edit(self, image: ImageData, prompt: str) -> ImageData:
        try:
            result = self.client.image_to_image(image.data, prompt=prompt, model=self.model)
        except InferenceTimeoutError:
            raise AIError("El modelo de imágenes tardó demasiado. Inténtalo de nuevo") from None
        except (HfHubHTTPError, ValueError) as error:
            logger.warning("ai.huggingface model=%s error=%s", self.model, error)
            raise AIError("El modelo de imágenes no pudo procesar la foto. Inténtalo de nuevo") from None
        buffer = io.BytesIO()
        result.convert("RGB").save(buffer, "JPEG", quality=90)
        return ImageData(buffer.getvalue(), "image/jpeg")
