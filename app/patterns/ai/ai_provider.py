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
