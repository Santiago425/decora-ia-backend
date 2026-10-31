from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PaletteResponse(ORMModel):
    id: int
    name: str
    colors: list[str]
    style_id: int | None = None


class MaterialResponse(ORMModel):
    id: int
    slug: str
    name: str
    surface: str
    color_hex: str
    roughness: float
    metalness: float
    price_per_unit: Decimal


class StyleResponse(ORMModel):
    id: int
    slug: str
    name: str
    description: str
    image_url: str | None
    lighting_color: str
    lighting_intensity: float
    palettes: list[PaletteResponse]
    materials: list[MaterialResponse]


class RoomTypeResponse(ORMModel):
    id: int
    slug: str
    name: str
    icon: str


class FurnitureCategoryResponse(ORMModel):
    id: int
    slug: str
    name: str
    icon: str
    shape: str


class FurnitureItemResponse(ORMModel):
    id: int
    name: str
    description: str
    price: Decimal
    width: float
    depth: float
    height: float
    default_color: str
    model_url: str | None
    category: FurnitureCategoryResponse
