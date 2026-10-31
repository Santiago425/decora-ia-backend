import uuid
from copy import deepcopy

from app.models import FurnitureItem

SCENE_FORMAT = 1
WALL_GAP = 0.05
CORNER_GAP = 0.4
ANCHOR_SHAPES = ("bed", "sofa", "desk", "cabinet", "shelf")


def new_node_id() -> str:
    return f"n-{uuid.uuid4().hex[:10]}"


# Builder: assembles a scene step by step so every project starts from a valid room.
class RoomBuilder:
    def __init__(self, width: float, length: float, height: float) -> None:
        self._room = {"width": width, "length": length, "height": height, "wall_material": None, "floor_material": None}
        self._lighting = {"color": "#fff4e0", "intensity": 1.0}
        self._nodes: list[dict] = []

    @property
    def width(self) -> float:
        return self._room["width"]

    @property
    def length(self) -> float:
        return self._room["length"]

    def with_walls(self, material_slug: str | None) -> "RoomBuilder":
        self._room["wall_material"] = material_slug
        return self

    def with_floor(self, material_slug: str | None) -> "RoomBuilder":
        self._room["floor_material"] = material_slug
        return self

    def with_lighting(self, color: str, intensity: float) -> "RoomBuilder":
        self._lighting = {"color": color, "intensity": intensity}
        return self

    def add_furniture(self, item: FurnitureItem, x: float, z: float, rotation: float = 0) -> "RoomBuilder":
        self._nodes.append(
            {
                "id": new_node_id(),
                "kind": "item",
                "furniture_id": item.id,
                "name": item.name,
                "category": item.category.slug,
                "shape": item.category.shape,
                "position": [round(x, 3), round(z, 3)],
                "rotation": rotation,
                "size": [item.width, item.depth, item.height],
                "color": item.default_color,
                "price": float(item.price),
                "finish": None,
                "addons": [],
            }
        )
        return self

    def build(self) -> dict:
        return {"format": SCENE_FORMAT, "room": dict(self._room), "lighting": dict(self._lighting), "nodes": deepcopy(self._nodes)}


# Director: knows where each kind of furniture usually goes and drives the builder.
class StarterLayoutDirector:
    def __init__(self, builder: RoomBuilder) -> None:
        self.builder = builder

    def furnish(self, items: list[FurnitureItem]) -> RoomBuilder:
        half_w, half_l = self.builder.width / 2, self.builder.length / 2
        anchors = [item for item in items if item.category.shape in ANCHOR_SHAPES]
        anchors.sort(key=lambda item: ANCHOR_SHAPES.index(item.category.shape))
        walls = [
            lambda item: (0, -half_l + item.depth / 2 + WALL_GAP, 0),
            lambda item: (-half_w + item.depth / 2 + WALL_GAP, 0, 90),
            lambda item: (half_w - item.depth / 2 - WALL_GAP, 0, -90),
        ]
        for item, place in zip(anchors, walls, strict=False):
            self.builder.add_furniture(item, *place(item))

        for item in items:
            shape = item.category.shape
            if shape == "rug":
                self.builder.add_furniture(item, 0, 0.2)
            elif shape == "table":
                self.builder.add_furniture(item, 0, 0.3 if anchors else 0)
            elif shape == "chair":
                self.builder.add_furniture(item, half_w / 2, half_l / 2, -135)
            elif shape == "lamp":
                self.builder.add_furniture(item, -half_w + CORNER_GAP, -half_l + CORNER_GAP)
            elif shape == "plant":
                self.builder.add_furniture(item, half_w - CORNER_GAP, -half_l + CORNER_GAP)
        return self.builder
