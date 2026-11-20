import io
import logging
import time

from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError, InferenceTimeoutError

from app.patterns.ai.ai_provider import AIError, ImageData, ImageEditor

logger = logging.getLogger("habita.ai")

# Status codes worth a second try: the provider is busy or restarting.
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
STATUS_MESSAGES = {
    401: "Hugging Face rechazó el token de acceso. Revisa la configuración del servidor",
    402: "La cuenta de Hugging Face se quedó sin créditos. Recárgala para seguir generando imágenes",
    403: "El token de Hugging Face no tiene permiso para usar Inference Providers",
    404: "El modelo de imágenes configurado no está disponible en ese proveedor",
}
DEFAULT_MESSAGE = "El modelo de imágenes no pudo procesar la foto. Inténtalo de nuevo"
TIMEOUT_MESSAGE = "El modelo de imágenes tardó demasiado. Inténtalo de nuevo"


def _status(error: HfHubHTTPError) -> int | None:
    response = getattr(error, "response", None)
    return getattr(response, "status_code", None)


# Adapter: wraps Hugging Face Inference Providers (image-to-image) behind the ImageEditor interface.
class HuggingFaceImageEditor(ImageEditor):
    name = "huggingface"

    def __init__(
        self, token: str, provider: str, model: str, timeout: float, retries: int = 0, retry_delay: float = 0
    ) -> None:
        if not token or not model:
            raise AIError("Falta configurar Hugging Face (HUGGINGFACE_API_TOKEN y HUGGINGFACE_IMAGE_MODEL)")
        self.model = model
        self.provider = provider or "auto"
        self.retries = retries
        self.retry_delay = retry_delay
        self.client = InferenceClient(provider=self.provider, api_key=token, timeout=timeout)

    def edit(self, image: ImageData, prompt: str) -> ImageData:
        attempt = 0
        while True:
            try:
                result = self.client.image_to_image(image.data, prompt=prompt, model=self.model)
                break
            except InferenceTimeoutError:
                message, retryable, detail = TIMEOUT_MESSAGE, True, "timeout"
            except HfHubHTTPError as error:
                status = _status(error)
                message = STATUS_MESSAGES.get(status, DEFAULT_MESSAGE)
                retryable, detail = status in RETRYABLE_STATUS, f"status={status} error={error}"
            except ValueError as error:
                message, retryable, detail = DEFAULT_MESSAGE, False, f"error={error}"
            logger.warning(
                "ai.huggingface provider=%s model=%s attempt=%d %s", self.provider, self.model, attempt + 1, detail
            )
            if not retryable or attempt >= self.retries:
                raise AIError(message) from None
            attempt += 1
            time.sleep(self.retry_delay * attempt)
        buffer = io.BytesIO()
        result.convert("RGB").save(buffer, "JPEG", quality=90)
        return ImageData(buffer.getvalue(), "image/jpeg")
