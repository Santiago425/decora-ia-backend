import re
import unicodedata
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

PAGES = {
    "dashboard": "/",
    "redesign": "/redesign",
    "editor": "/editor",
    "projects": "/projects",
    "assistant": "/assistant",
    "docs": "/docs",
    "admin": "/admin",
}
EDITOR_ACTIONS = {
    "add_furniture",
    "change_style",
    "change_wall",
    "change_floor",
    "set_lighting",
    "undo",
    "redo",
    "rotate_selected",
    "remove_selected",
    "duplicate_selected",
}
ACTION_TYPES = EDITOR_ACTIONS | {"navigate", "create_project", "start_redesign"}


def normalize(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in plain if not unicodedata.combining(char))


def contains_word(text: str, phrase: str) -> bool:
    return re.search(rf"\b{re.escape(phrase)}\b", text) is not None


@dataclass(frozen=True)
class CatalogFurniture:
    id: int
    name: str
    category: str
    price: float


@dataclass(frozen=True)
class Vocabulary:
    styles: dict[str, str]
    style_descriptions: dict[str, str]
    room_types: dict[str, str]
    categories: dict[str, str]
    furniture: list[CatalogFurniture]
    walls: dict[str, str]
    floors: dict[str, str]

    def cheapest_in(self, category: str) -> CatalogFurniture | None:
        items = [item for item in self.furniture if item.category == category]
        return min(items, key=lambda item: item.price) if items else None

    def furniture_by_id(self, furniture_id: int) -> CatalogFurniture | None:
        return next((item for item in self.furniture if item.id == furniture_id), None)


@dataclass(frozen=True)
class AssistantContext:
    assistant_name: str
    page: str
    project_name: str | None = None
    project_count: int = 0
    total_budget: float = 0
    history: list[tuple[str, str]] = field(default_factory=list)

    @property
    def in_editor(self) -> bool:
        return self.page == "editor" and self.project_name is not None


class AssistantAction(BaseModel):
    type: str = Field(max_length=40)
    params: dict = Field(default_factory=dict)


class Interpretation(BaseModel):
    reply: str = Field(max_length=1200)
    intent: str = Field(default="chat", max_length=40)
    actions: list[AssistantAction] = Field(default_factory=list, max_length=6)
