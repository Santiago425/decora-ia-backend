from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


# Composite: a line and a section answer the same questions (total, bought, count), so the list, each
# section and each line are added up the same way no matter how deep they are nested.
class ShoppingNode(ABC):
    key: str
    title: str

    @abstractmethod
    def total(self) -> float: ...

    @abstractmethod
    def purchased_total(self) -> float: ...

    @abstractmethod
    def lines(self) -> list[ShoppingLine]: ...


@dataclass
class ShoppingLine(ShoppingNode):
    key: str
    title: str
    detail: str
    unit: str
    quantity: float
    unit_price: float
    purchased: bool = False

    def total(self) -> float:
        return round(self.quantity * self.unit_price, 2)

    def purchased_total(self) -> float:
        return self.total() if self.purchased else 0.0

    def lines(self) -> list[ShoppingLine]:
        return [self]


@dataclass
class ShoppingSection(ShoppingNode):
    key: str
    title: str
    children: list[ShoppingNode] = field(default_factory=list)

    def add(self, node: ShoppingNode) -> ShoppingSection:
        self.children.append(node)
        return self

    def total(self) -> float:
        return round(sum(child.total() for child in self.children), 2)

    def purchased_total(self) -> float:
        return round(sum(child.purchased_total() for child in self.children), 2)

    def lines(self) -> list[ShoppingLine]:
        return [line for child in self.children for line in child.lines()]


def budget_status(total: float, limit: float | None, warning_ratio: float) -> str:
    if limit is None or limit <= 0:
        return "none"
    if total > limit:
        return "over"
    return "near" if total >= limit * warning_ratio else "under"
