import uuid
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field

LineKey = Annotated[str, Field(min_length=1, max_length=120)]


class ShoppingLineOut(BaseModel):
    key: str
    title: str
    detail: str
    unit: str
    quantity: float
    unit_price: float
    total: float
    purchased: bool


class ShoppingSectionOut(BaseModel):
    key: str
    title: str
    total: float
    purchased_total: float
    lines: list[ShoppingLineOut]


class ShoppingListOut(BaseModel):
    project_id: uuid.UUID
    project_name: str
    currency: str
    include_redesign: bool
    has_redesign: bool
    sections: list[ShoppingSectionOut]
    total: float
    purchased_total: float
    pending_total: float
    item_count: int
    purchased_count: int
    budget_limit: float | None
    budget_remaining: float | None
    budget_used_ratio: float | None
    budget_status: Literal["none", "under", "near", "over"]


class BudgetLimitUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, ge=0, le=Decimal("999999999999"))


class PurchasedUpdate(BaseModel):
    keys: list[LineKey] = Field(default_factory=list, max_length=300)
