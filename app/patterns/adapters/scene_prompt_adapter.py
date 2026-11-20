from collections import Counter

from app.models import DaylightPreset, DesignStyle, Material, RoomType

MAX_PIECES = 12
DEFAULT_LIGHT = "soft natural interior light"


def _items(nodes: list[dict]) -> list[dict]:
    found = []
    for node in nodes:
        if node.get("kind") == "group":
            found.extend(_items(node.get("children", [])))
        elif node.get("kind") == "item":
            found.append(node)
    return found


def _count(shape: str, amount: int) -> str:
    noun = shape.replace("_", " ")
    return f"a {noun}" if amount == 1 else f"{amount} {noun}s"


# Adapter: the image model only understands one English instruction, so this class
# translates the editor's scene JSON (pieces, finishes, time of day) into that instruction.
class ScenePromptAdapter:
    def __init__(
        self,
        scene: dict,
        room_type: RoomType | None,
        style: DesignStyle | None,
        materials: dict[str, Material],
        daylight: DaylightPreset | None,
    ) -> None:
        self.scene = scene or {}
        self.room_type = room_type
        self.style = style
        self.materials = materials
        self.daylight = daylight

    def pieces(self) -> list[str]:
        shapes = Counter(item.get("shape", "piece") for item in _items(self.scene.get("nodes", [])))
        return [_count(shape, amount) for shape, amount in shapes.most_common(MAX_PIECES)]

    def finish(self, key: str) -> str | None:
        slug = (self.scene.get("room") or {}).get(key)
        material = self.materials.get(slug) if slug else None
        return f"{material.name} ({material.color_hex})" if material else None

    def light(self) -> str:
        return self.daylight.prompt if self.daylight and self.daylight.prompt else DEFAULT_LIGHT

    def prompt(self) -> str:
        room = self.room_type.slug.replace("_", " ") if self.room_type else "room"
        style = f" in {self.style.slug.replace('-', ' ')} style" if self.style else ""
        lines = [
            f"Turn this 3D render of a {room}{style} into a photorealistic interior photograph.",
            "Keep the exact camera angle, the room shape and the position, size and color of every piece.",
        ]
        pieces = self.pieces()
        if pieces:
            lines.append(f"The room has {', '.join(pieces)}.")
        walls, floor = self.finish("wall_material"), self.finish("floor_material")
        if walls:
            lines.append(f"Walls finished in {walls}.")
        if floor:
            lines.append(f"Floor made of {floor}.")
        lines.append(f"Lighting: {self.light()}.")
        lines.append(
            "Use real materials with natural textures, soft shadows and reflections. "
            "Do not add or remove furniture, no people and no text."
        )
        return " ".join(lines)
