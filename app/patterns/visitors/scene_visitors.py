from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator


# Visitor: operations over the scene (budget, counting) live outside the scene data; each node calls back
# the method that matches its own type through accept().
class SceneVisitor(ABC):
    @abstractmethod
    def visit_room(self, room: dict) -> None: ...

    @abstractmethod
    def visit_group(self, group: dict) -> None: ...

    @abstractmethod
    def visit_item(self, item: dict) -> None: ...


class SceneElement(ABC):
    def __init__(self, data: dict) -> None:
        self.data = data

    @abstractmethod
    def accept(self, visitor: SceneVisitor) -> None: ...


class RoomElement(SceneElement):
    def accept(self, visitor: SceneVisitor) -> None:
        visitor.visit_room(self.data)


class GroupElement(SceneElement):
    def accept(self, visitor: SceneVisitor) -> None:
        visitor.visit_group(self.data)


class ItemElement(SceneElement):
    def accept(self, visitor: SceneVisitor) -> None:
        visitor.visit_item(self.data)


# Iterator: walks the room and every nested node depth first without exposing how groups store children.
class SceneIterator(Iterator[SceneElement]):
    def __init__(self, scene: dict) -> None:
        self._pending: list[SceneElement] = [
            *reversed(self._wrap(scene.get("nodes", []))),
            RoomElement(scene.get("room", {})),
        ]

    @staticmethod
    def _wrap(nodes: list[dict]) -> list[SceneElement]:
        return [GroupElement(node) if node.get("kind") == "group" else ItemElement(node) for node in nodes]

    def __iter__(self) -> SceneIterator:
        return self

    def __next__(self) -> SceneElement:
        if not self._pending:
            raise StopIteration
        element = self._pending.pop()
        if isinstance(element, GroupElement):
            self._pending.extend(reversed(self._wrap(element.data.get("children", []))))
        return element


def walk_scene[V: SceneVisitor](scene: dict, visitor: V) -> V:
    for element in SceneIterator(scene):
        element.accept(visitor)
    return visitor


class BudgetVisitor(SceneVisitor):
    def __init__(self, furniture: dict[int, float], materials: dict[str, float], addons: dict[str, float]) -> None:
        self.furniture = furniture
        self.materials = materials
        self.addons = addons
        self.total = 0.0

    def visit_room(self, room):
        width, length, height = room.get("width", 0), room.get("length", 0), room.get("height", 0)
        self.total += width * length * self.materials.get(room.get("floor_material") or "", 0)
        self.total += 2 * (width + length) * height * self.materials.get(room.get("wall_material") or "", 0)

    def visit_group(self, group):
        pass

    def visit_item(self, item):
        self.total += self.furniture.get(item.get("furniture_id"), 0)
        self.total += sum(self.addons.get(slug, 0) for slug in item.get("addons", []))


class FurnitureIdCollector(SceneVisitor):
    def __init__(self) -> None:
        self.ids: set[int] = set()
        self.count = 0

    def visit_room(self, room):
        pass

    def visit_group(self, group):
        pass

    def visit_item(self, item):
        self.count += 1
        if isinstance(item.get("furniture_id"), int):
            self.ids.add(item["furniture_id"])


class ShoppingVisitor(SceneVisitor):
    """Counts what has to be bought: pieces by catalog id, add-ons by slug and square meters per surface."""

    def __init__(self) -> None:
        self.furniture: dict[int, int] = {}
        self.custom: dict[str, tuple[int, float]] = {}
        self.addons: dict[str, int] = {}
        self.surfaces: dict[tuple[str, str], float] = {}

    def visit_room(self, room):
        width, length, height = room.get("width", 0), room.get("length", 0), room.get("height", 0)
        self._add_surface("floor", room.get("floor_material"), width * length)
        self._add_surface("wall", room.get("wall_material"), 2 * (width + length) * height)

    def visit_group(self, group):
        pass

    def visit_item(self, item):
        furniture_id = item.get("furniture_id")
        if isinstance(furniture_id, int):
            self.furniture[furniture_id] = self.furniture.get(furniture_id, 0) + 1
        else:
            name = item.get("name", "")
            count, _ = self.custom.get(name, (0, 0.0))
            self.custom[name] = (count + 1, float(item.get("price", 0)))
        for slug in item.get("addons", []):
            self.addons[slug] = self.addons.get(slug, 0) + 1

    def _add_surface(self, surface: str, slug: str | None, area: float) -> None:
        if slug and area > 0:
            self.surfaces[(surface, slug)] = self.surfaces.get((surface, slug), 0) + area
