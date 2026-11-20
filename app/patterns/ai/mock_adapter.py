import io

from PIL import Image, ImageEnhance, ImageOps

from app.patterns.ai.ai_provider import (
    DesignAdvisor,
    DesignSuggestions,
    ImageData,
    ImageEditor,
    StyleDescriber,
    StyleDescription,
)


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


class MockStyleDescriber(StyleDescriber):
    """Offline describer for development and tests: reads the dominant colors of the inspiration photo."""

    name = "mock"
    max_colors = 4

    def describe(self, image: ImageData) -> StyleDescription:
        photo = ImageOps.exif_transpose(Image.open(io.BytesIO(image.data))).convert("RGB")
        photo.thumbnail((128, 128))
        quantized = photo.quantize(colors=self.max_colors)
        palette = quantized.getpalette() or []
        ranked = sorted(quantized.getcolors() or [], reverse=True)
        colors = ["#{:02x}{:02x}{:02x}".format(*palette[index * 3 : index * 3 + 3]) for _, index in ranked]
        return StyleDescription(
            name="Inspiración",
            summary=f"Tonos tomados de tu foto: {', '.join(colors)}.",
            prompt=f"a calm, cohesive interior that follows the mood of the reference photo, dominated by {', '.join(colors)}.",
            colors=colors,
        )
