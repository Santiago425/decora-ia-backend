from __future__ import annotations

import re
from dataclasses import dataclass

from app.models import DesignStyle, RoomType
from app.patterns.ai.ai_provider import ImageData
from app.patterns.strategies.budget_strategies import BudgetStrategy

HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
MAX_COLORS = 6


class RedesignRequestError(ValueError):
    pass


@dataclass(frozen=True)
class RedesignRequest:
    image: ImageData
    room_type: RoomType
    style: DesignStyle
    palette: tuple[str, ...]
    budget: float | None
    keep_structure: bool
    budget_strategy: BudgetStrategy
    currency: str
    variation: int

    def image_prompt(self) -> str:
        lines = [
            f"Redesign this {self.room_type.slug.replace('_', ' ')} photo in a {self.style.slug} interior design style "
            f"({self.style.description}).",
            "Return a photorealistic image taken from the same camera angle, with natural light and real furniture.",
        ]
        if self.keep_structure:
            lines.append("Keep the room structure exactly the same: walls, windows, doors, ceiling and floor layout.")
        if self.palette:
            lines.append(f"Use this color palette: {', '.join(self.palette)}.")
        materials = ", ".join(material.name for material in self.style.materials)
        if materials:
            lines.append(f"Suggested materials: {materials}.")
        if self.variation:
            lines.append(f"Create an alternative version #{self.variation} with a different furniture arrangement.")
        return " ".join(lines)

    def advice_prompt(self) -> str:
        budget = f"Presupuesto total: {self.budget:,.0f} {self.currency}." if self.budget else "Sin presupuesto fijo."
        palette = f"Paleta elegida: {', '.join(self.palette)}." if self.palette else ""
        return (
            f"Eres una diseñadora de interiores. Mira la foto de este espacio ({self.room_type.name}) y propón cómo "
            f"rediseñarlo en estilo {self.style.name}. {budget} {palette} {self.budget_strategy.prompt_hint} "
            f"Responde solo con JSON con esta forma: "
            '{"summary": str, "furniture": [{"name": str, "description": str, "price": number}], '
            '"colors": [{"name": str, "hex": "#RRGGBB"}], "materials": [{"name": str, "description": str, "price": number}], '
            '"lighting": [{"name": str, "description": str, "price": number}]}. '
            f"Precios aproximados en {self.currency}, textos cortos en español, máximo 5 muebles, 5 colores, 4 materiales y 3 luces."
        )


# Builder: assembles the AI request step by step and validates it once at the end.
class RedesignRequestBuilder:
    def __init__(self, currency: str) -> None:
        self._currency = currency
        self._image: ImageData | None = None
        self._room_type: RoomType | None = None
        self._style: DesignStyle | None = None
        self._palette: list[str] = []
        self._budget: float | None = None
        self._keep_structure = True
        self._strategy: BudgetStrategy | None = None
        self._variation = 0

    def with_photo(self, image: ImageData) -> RedesignRequestBuilder:
        self._image = image
        return self

    def for_room(self, room_type: RoomType | None) -> RedesignRequestBuilder:
        self._room_type = room_type
        return self

    def in_style(self, style: DesignStyle | None) -> RedesignRequestBuilder:
        self._style = style
        return self

    def with_palette(self, colors: list[str] | None) -> RedesignRequestBuilder:
        self._palette = list(colors or [])
        return self

    def with_budget(self, amount: float | None, strategy: BudgetStrategy) -> RedesignRequestBuilder:
        self._budget = amount
        self._strategy = strategy
        return self

    def keeping_structure(self, keep: bool = True) -> RedesignRequestBuilder:
        self._keep_structure = keep
        return self

    def as_variation(self, number: int) -> RedesignRequestBuilder:
        self._variation = number
        return self

    def build(self) -> RedesignRequest:
        if self._image is None:
            raise RedesignRequestError("Sube una foto del espacio")
        if self._room_type is None:
            raise RedesignRequestError("Elige un tipo de habitación válido")
        if self._style is None:
            raise RedesignRequestError("Elige un estilo válido")
        if len(self._palette) > MAX_COLORS or not all(HEX_COLOR.match(c) for c in self._palette):
            raise RedesignRequestError(f"La paleta admite hasta {MAX_COLORS} colores en formato #RRGGBB")
        if self._budget is not None and self._budget < 0:
            raise RedesignRequestError("El presupuesto no puede ser negativo")
        if self._strategy is None:
            raise RedesignRequestError("Falta la estrategia de presupuesto")
        return RedesignRequest(
            image=self._image,
            room_type=self._room_type,
            style=self._style,
            palette=tuple(c.lower() for c in self._palette),
            budget=self._budget,
            keep_structure=self._keep_structure,
            budget_strategy=self._strategy,
            currency=self._currency,
            variation=self._variation,
        )
