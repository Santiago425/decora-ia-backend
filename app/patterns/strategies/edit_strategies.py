import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
MAX_TEXT = 80
UNTOUCHED = (
    "Change nothing else: keep the furniture, walls, floor, ceiling, windows, doors, lighting "
    "and the exact camera angle as they are. Return a photorealistic image."
)


class EditRequestError(ValueError):
    pass


@dataclass(frozen=True)
class EditField:
    key: str
    label: str
    kind: str  # color | text | material
    placeholder: str = ""
    surface: str | None = None


# Strategy: each targeted edit knows its fields and how to phrase one precise instruction for the image model.
class EditStrategy(ABC):
    key: str
    label: str
    description: str
    fields: tuple[EditField, ...]

    def clean(self, raw: dict[str, str]) -> dict[str, str]:
        cleaned = {}
        for edit_field in self.fields:
            value = " ".join(str(raw.get(edit_field.key, "")).split())[:MAX_TEXT]
            if not value:
                raise EditRequestError(f"Completa «{edit_field.label}»")
            if edit_field.kind == "color" and not HEX_COLOR.match(value):
                raise EditRequestError("El color debe tener el formato #RRGGBB")
            cleaned[edit_field.key] = value.lower() if edit_field.kind == "color" else value
        return cleaned

    def prompt(self, values: dict[str, str], keep_items: str | None = None) -> str:
        lines = [self.instruction(values), UNTOUCHED]
        if keep_items:
            lines.append(f"These pieces must stay exactly as they are: {keep_items}.")
        return " ".join(lines)

    @abstractmethod
    def instruction(self, values: dict[str, str]) -> str: ...


class WallPaintEdit(EditStrategy):
    key = "wall_paint"
    label = "Pintar paredes"
    description = "Cambia solo el color de las paredes."
    fields = (EditField("color", "Color de pintura", "color"),)

    def instruction(self, values: dict[str, str]) -> str:
        return f"Repaint only the walls with a matte paint of color {values['color']}, with realistic shading."


class FloorSwapEdit(EditStrategy):
    key = "floor_swap"
    label = "Cambiar piso"
    description = "Reemplaza el piso por un material del catálogo."
    fields = (EditField("material", "Material del piso", "material", surface="floor"),)

    def instruction(self, values: dict[str, str]) -> str:
        return f"Replace only the floor with {values['material']}, following the room perspective."


class RemoveObjectEdit(EditStrategy):
    key = "remove_object"
    label = "Borrar objeto"
    description = "Quita algo de la foto y rellena el espacio."
    fields = (EditField("target", "¿Qué quieres borrar?", "text", "Ej.: la silla roja junto a la ventana"),)

    def instruction(self, values: dict[str, str]) -> str:
        return (
            f"Remove {values['target']} from the photo and fill that area naturally with the surrounding "
            "floor and wall."
        )


class ReplaceFurnitureEdit(EditStrategy):
    key = "replace_furniture"
    label = "Cambiar un mueble"
    description = "Cambia un mueble por otro en el mismo lugar."
    fields = (
        EditField("target", "Mueble actual", "text", "Ej.: el sofá gris"),
        EditField("replacement", "Nuevo mueble", "text", "Ej.: un sofá de lino beige con patas de madera"),
    )

    def instruction(self, values: dict[str, str]) -> str:
        return (
            f"Replace {values['target']} with {values['replacement']}, in the same position and scale, "
            "matching the light of the room."
        )


EDIT_STRATEGIES: dict[str, EditStrategy] = {
    strategy.key: strategy
    for strategy in (WallPaintEdit(), FloorSwapEdit(), RemoveObjectEdit(), ReplaceFurnitureEdit())
}


def select_edit_strategy(key: str) -> EditStrategy:
    strategy = EDIT_STRATEGIES.get(key)
    if strategy is None:
        raise EditRequestError("Esa herramienta de edición no existe")
    return strategy
