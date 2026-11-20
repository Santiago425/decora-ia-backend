from decimal import Decimal

from sqlalchemy import JSON, Boolean, Column, Float, ForeignKey, Integer, Numeric, String, Table, Text, text, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

style_materials = Table(
    "style_materials",
    Base.metadata,
    Column("style_id", ForeignKey("design_styles.id", ondelete="CASCADE"), primary_key=True),
    Column("material_id", ForeignKey("materials.id", ondelete="CASCADE"), primary_key=True),
)


class DesignStyle(Base):
    __tablename__ = "design_styles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(60))
    description: Mapped[str] = mapped_column(Text, default="")
    image_url: Mapped[str | None] = mapped_column(String(500))
    lighting_color: Mapped[str] = mapped_column(String(7), default="#fff4e0")
    lighting_intensity: Mapped[float] = mapped_column(Float, default=1.0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    palettes: Mapped[list["ColorPalette"]] = relationship(back_populates="style", cascade="all, delete-orphan")
    materials: Mapped[list["Material"]] = relationship(secondary=style_materials)


class ColorPalette(Base):
    __tablename__ = "color_palettes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    style_id: Mapped[int | None] = mapped_column(ForeignKey("design_styles.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(60))
    colors: Mapped[list[str]] = mapped_column(JSON, default=list)

    style: Mapped[DesignStyle | None] = relationship(back_populates="palettes")


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(60))
    surface: Mapped[str] = mapped_column(String(20))
    color_hex: Mapped[str] = mapped_column(String(7))
    roughness: Mapped[float] = mapped_column(Float, default=0.8)
    metalness: Mapped[float] = mapped_column(Float, default=0.0)
    price_per_unit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    texture_url: Mapped[str | None] = mapped_column(String(500))


class RoomType(Base):
    __tablename__ = "room_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(60))
    icon: Mapped[str] = mapped_column(String(40), default="home")
    cover_image_url: Mapped[str | None] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class FurnitureCategory(Base):
    __tablename__ = "furniture_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(60))
    icon: Mapped[str] = mapped_column(String(40), default="box")
    shape: Mapped[str] = mapped_column(String(40))
    room_types: Mapped[list[str]] = mapped_column(JSON, default=list)
    # False for pieces that hang on the wall (art, curtains, a TV), so they never block the floor below them.
    blocks_floor: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())

    items: Mapped[list["FurnitureItem"]] = relationship(back_populates="category")


class FurnitureItem(Base):
    __tablename__ = "furniture_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("furniture_categories.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    width: Mapped[float] = mapped_column(Float)
    depth: Mapped[float] = mapped_column(Float)
    height: Mapped[float] = mapped_column(Float)
    default_color: Mapped[str] = mapped_column(String(7))
    model_url: Mapped[str | None] = mapped_column(String(500))
    materials: Mapped[str] = mapped_column(String(160), default="", server_default="")
    # Colors the piece is sold in, as [{"name": ..., "hex": ...}], and the furniture finishes that suit it.
    color_options: Mapped[list[dict]] = mapped_column(JSON, default=list, server_default=text("'[]'"))
    finish_options: Mapped[list[str]] = mapped_column(JSON, default=list, server_default=text("'[]'"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    category: Mapped[FurnitureCategory] = relationship(back_populates="items")


class FurnitureAddon(Base):
    __tablename__ = "furniture_addons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    visual: Mapped[str] = mapped_column(String(20), default="none")
    icon: Mapped[str] = mapped_column(String(40), default="sparkles", server_default="sparkles")
    color_hex: Mapped[str | None] = mapped_column(String(7))
    categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class InspirationPhoto(Base):
    __tablename__ = "inspiration_photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(80))
    image_url: Mapped[str] = mapped_column(String(500))
    author_name: Mapped[str] = mapped_column(String(80), default="")
    source_url: Mapped[str | None] = mapped_column(String(500))
    style_id: Mapped[int | None] = mapped_column(ForeignKey("design_styles.id", ondelete="SET NULL"))
    room_type_id: Mapped[int | None] = mapped_column(ForeignKey("room_types.id", ondelete="SET NULL"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    style: Mapped[DesignStyle | None] = relationship()
    room_type: Mapped[RoomType | None] = relationship()


class DaylightPreset(Base):
    """A time of day for the 3D editor: where the sun is, its color, and how bright windows and lamps are."""

    __tablename__ = "daylight_presets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(60))
    description: Mapped[str] = mapped_column(String(200), default="")
    sun_color: Mapped[str] = mapped_column(String(7))
    sun_intensity: Mapped[float] = mapped_column(Float)
    sun_elevation: Mapped[float] = mapped_column(Float)
    sun_azimuth: Mapped[float] = mapped_column(Float)
    ambient_color: Mapped[str] = mapped_column(String(7))
    ambient_intensity: Mapped[float] = mapped_column(Float)
    sky_color: Mapped[str] = mapped_column(String(7))
    window_intensity: Mapped[float] = mapped_column(Float, default=0)
    lamp_intensity: Mapped[float] = mapped_column(Float, default=0)
    # English description of the light, added to the prompt when a 3D view is turned into a photo.
    prompt: Mapped[str] = mapped_column(String(300), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
