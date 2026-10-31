from abc import ABC, abstractmethod

from app.models import FurnitureItem


# Strategy: interchangeable ways to choose products and phrase the request according to the budget level.
class BudgetStrategy(ABC):
    key: str
    label: str
    prompt_hint: str

    def pick(
        self, items_by_category: dict[str, list[FurnitureItem]], limit: int, budget: float | None = None
    ) -> list[FurnitureItem]:
        picks, remaining = [], budget
        for items in items_by_category.values():
            affordable = [i for i in items if remaining is None or float(i.price) <= remaining]
            if not affordable:
                continue
            choice = self.choose(sorted(affordable, key=lambda i: i.price))
            picks.append(choice)
            if remaining is not None:
                remaining -= float(choice.price)
            if len(picks) == limit:
                break
        return picks

    @abstractmethod
    def choose(self, items_by_price: list[FurnitureItem]) -> FurnitureItem: ...


class EconomicBudget(BudgetStrategy):
    key, label = "economic", "Económico"
    prompt_hint = "Prioriza opciones económicas, cambios de pintura, textiles y piezas de bajo costo."

    def choose(self, items_by_price):
        return items_by_price[0]


class StandardBudget(BudgetStrategy):
    key, label = "standard", "Gama media"
    prompt_hint = "Propón productos de gama media con buena relación calidad-precio."

    def choose(self, items_by_price):
        return items_by_price[(len(items_by_price) - 1) // 2]


class PremiumBudget(BudgetStrategy):
    key, label = "premium", "Premium"
    prompt_hint = "Propón materiales nobles, piezas de diseño y acabados premium."

    def choose(self, items_by_price):
        return items_by_price[-1]


STRATEGIES: dict[str, BudgetStrategy] = {s.key: s for s in (EconomicBudget(), StandardBudget(), PremiumBudget())}


def select_budget_strategy(budget: float | None, economic_max: float, standard_max: float) -> BudgetStrategy:
    if budget is None:
        return STRATEGIES["standard"]
    if budget <= economic_max:
        return STRATEGIES["economic"]
    if budget <= standard_max:
        return STRATEGIES["standard"]
    return STRATEGIES["premium"]
