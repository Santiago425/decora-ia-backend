import io

from PIL import Image, ImageEnhance, ImageOps

from app.patterns.ai.ai_provider import DesignAdvisor, DesignSuggestions, ImageData, ImageEditor


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    return tuple(int(value[i : i + 2], 16) for i in (1, 3, 5))


class MockImageEditor(ImageEditor):
    """Offline editor for development and tests: tints the photo with the chosen palette."""

    name = "mock"

    def __init__(self, palette: list[str] | None = None) -> None:
        self.palette = palette or ["#e3d3bb", "#a9b49a"]

    def edit(self, image: ImageData, prompt: str) -> ImageData:
        photo = ImageOps.exif_transpose(Image.open(io.BytesIO(image.data))).convert("RGB")
        photo = ImageEnhance.Brightness(ImageEnhance.Color(photo).enhance(0.75)).enhance(1.08)
        overlay = Image.new("RGB", photo.size, _hex_to_rgb(self.palette[len(prompt) % len(self.palette)]))
        result = Image.blend(photo, overlay, 0.22)
        buffer = io.BytesIO()
        result.save(buffer, "JPEG", quality=88)
        return ImageData(buffer.getvalue(), "image/jpeg")


class MockDesignAdvisor(DesignAdvisor):
    name = "mock"

    def __init__(self, suggestions: DesignSuggestions) -> None:
        self.suggestions = suggestions

    def suggest(self, image: ImageData, prompt: str) -> DesignSuggestions:
        return self.suggestions
