from abc import ABC, abstractmethod


# Visitor: operations over the scene tree (room, groups, items) live outside the scene data itself.
class SceneVisitor(ABC):
    @abstractmethod
    def visit_room(self, room: dict) -> None: ...

    @abstractmethod
    def visit_group(self, group: dict) -> None: ...

    @abstractmethod
    def visit_item(self, item: dict) -> None: ...


def walk_scene(scene: dict, visitor: SceneVisitor) -> SceneVisitor:
    visitor.visit_room(scene.get("room", {}))

    def visit(nodes: list[dict]) -> None:
        for node in nodes:
            if node.get("kind") == "group":
                visitor.visit_group(node)
                visit(node.get("children", []))
            else:
                visitor.visit_item(node)

    visit(scene.get("nodes", []))
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
