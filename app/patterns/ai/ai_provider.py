from abc import ABC, abstractmethod
from dataclasses import dataclass

from pydantic import BaseModel, Field


class AIError(Exception):
    def __init__(self, user_message: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message


@dataclass(frozen=True)
class ImageData:
    data: bytes
    content_type: str


class SuggestedItem(BaseModel):
    name: str = Field(max_length=120)
    description: str = Field(default="", max_length=300)
    price: float = Field(default=0, ge=0)


class SuggestedColor(BaseModel):
    name: str = Field(max_length=60)
    hex: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")


class DesignSuggestions(BaseModel):
    summary: str = Field(default="", max_length=600)
    furniture: list[SuggestedItem] = Field(default_factory=list, max_length=8)
    colors: list[SuggestedColor] = Field(default_factory=list, max_length=6)
    materials: list[SuggestedItem] = Field(default_factory=list, max_length=6)
    lighting: list[SuggestedItem] = Field(default_factory=list, max_length=4)

    def total(self) -> float:
        return sum(item.price for group in (self.furniture, self.materials, self.lighting) for item in group)


# Adapter targets: every AI provider is wrapped so the app talks to these two interfaces only.
class ImageEditor(ABC):
    name: str

    @abstractmethod
    def edit(self, image: ImageData, prompt: str) -> ImageData: ...


class DesignAdvisor(ABC):
    name: str

    @abstractmethod
    def suggest(self, image: ImageData, prompt: str) -> DesignSuggestions: ...


class StyleDescription(BaseModel):
    """What the text model read from an inspiration photo: a short Spanish summary and an English style brief."""

    name: str = Field(default="", max_length=80)
    summary: str = Field(default="", max_length=400)
    prompt: str = Field(min_length=1, max_length=800)
    colors: list[str] = Field(default_factory=list, max_length=6)

    def image_prompt(self, keep_structure: bool, keep_items: str | None = None) -> str:
        lines = [
            f"Restyle this room photo to match this interior design inspiration: {self.prompt}",
            "Return a photorealistic image taken from the same camera angle, with natural light and real furniture.",
        ]
        if keep_structure:
            lines.append(
                "Respect the real room: keep walls, windows, doors, ceiling and floor layout in the same place and "
                "size. Do not move, add or remove any window or door."
            )
        if keep_items:
            lines.append(f"Keep these existing pieces exactly as they are, in the same place: {keep_items}.")
        if self.colors:
            lines.append(f"Use this color palette: {', '.join(self.colors)}.")
        return " ".join(lines)


# Adapter target: a text model with vision reads the style of an inspiration photo and returns it as text.
class StyleDescriber(ABC):
    name: str

    @abstractmethod
    def describe(self, image: ImageData) -> StyleDescription: ...
