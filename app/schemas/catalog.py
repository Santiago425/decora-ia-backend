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
    texture_url: str | None = None


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
    cover_image_url: str | None = None


class CatalogRef(ORMModel):
    slug: str
    name: str


class InspirationPhotoResponse(ORMModel):
    id: int
    title: str
    image_url: str
    author_name: str
    source_url: str | None
    style: CatalogRef | None
    room_type: CatalogRef | None


class FurnitureCategoryResponse(ORMModel):
    id: int
    slug: str
    name: str
    icon: str
    shape: str
    room_types: list[str]
    blocks_floor: bool = True


class ColorOption(BaseModel):
    name: str
    hex: str


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
    materials: str = ""
    color_options: list[ColorOption] = []
    finish_options: list[str] = []
    category: FurnitureCategoryResponse


class FurnitureAddonResponse(ORMModel):
    id: int
    slug: str
    name: str
    description: str
    price: Decimal
    visual: str
    icon: str = "sparkles"
    color_hex: str | None
    categories: list[str]


class DaylightPresetResponse(ORMModel):
    id: int
    slug: str
    name: str
    description: str
    sun_color: str
    sun_intensity: float
    sun_elevation: float
    sun_azimuth: float
    ambient_color: str
    ambient_intensity: float
    sky_color: str
    window_intensity: float
    lamp_intensity: float
