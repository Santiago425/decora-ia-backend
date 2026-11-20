import uuid
from decimal import Decimal

from app.core.settings import Settings
from app.models import Project, Redesign, RedesignStatus, User
from app.patterns.composites.shopping_list import ShoppingLine, ShoppingSection, budget_status
from app.patterns.visitors.scene_visitors import ShoppingVisitor, walk_scene
from app.repositories import FurnitureAddonRepository, FurnitureRepository, MaterialRepository, ProjectRepository
from app.schemas.shopping_list import ShoppingLineOut, ShoppingListOut, ShoppingSectionOut

UNIT_PIECE = "unidad"
UNIT_AREA = "m²"
SURFACE_LABELS = {"floor": "Piso", "wall": "Paredes"}
SUGGESTION_GROUPS = {"furniture": "Muebles sugeridos", "materials": "Materiales sugeridos", "lighting": "Iluminación"}


class ShoppingProjectNotFound(Exception):
    pass


class ShoppingListService:
    def __init__(
        self,
        projects: ProjectRepository,
        furniture: FurnitureRepository,
        materials: MaterialRepository,
        addons: FurnitureAddonRepository,
        settings: Settings,
    ) -> None:
        self.projects = projects
        self.furniture = furniture
        self.materials = materials
        self.addons = addons
        self.settings = settings

    def get(self, user: User, project_id: uuid.UUID, include_redesign: bool = False) -> ShoppingListOut:
        project = self.owned(user, project_id)
        root = self.build(project, include_redesign)
        return self._to_out(project, root, include_redesign)

    def set_budget(
        self, user: User, project_id: uuid.UUID, amount: Decimal | None, include_redesign: bool = False
    ) -> ShoppingListOut:
        project = self.owned(user, project_id)
        project.budget_limit = amount if amount else None
        self.projects.session.commit()
        return self.get(user, project_id, include_redesign)

    def set_purchased(
        self, user: User, project_id: uuid.UUID, keys: list[str], include_redesign: bool = False
    ) -> ShoppingListOut:
        project = self.owned(user, project_id)
        project.purchased_items = list(dict.fromkeys(keys))[: self.settings.shopping_max_purchased]
        self.projects.session.commit()
        return self.get(user, project_id, include_redesign)

    def build(self, project: Project, include_redesign: bool = False) -> ShoppingSection:
        purchased = set(project.purchased_items or [])
        counts = walk_scene(project.scene or {}, ShoppingVisitor())
        root = ShoppingSection("list", project.name)
        root.add(self._furniture_section(counts, purchased))
        root.add(self._addon_section(counts, purchased))
        root.add(self._finish_section(counts, purchased))
        redesign = self._latest_redesign(project)
        if include_redesign and redesign is not None:
            root.add(self._redesign_section(redesign, purchased))
        root.children = [section for section in root.children if section.lines()]
        return root

    def _furniture_section(self, counts: ShoppingVisitor, purchased: set[str]) -> ShoppingSection:
        section = ShoppingSection("furniture", "Muebles")
        items = self.furniture.by_ids(set(counts.furniture))
        for furniture_id, quantity in counts.furniture.items():
            item = items.get(furniture_id)
            if item is None:
                continue
            key = f"furniture:{furniture_id}"
            section.add(
                ShoppingLine(
                    key, item.name, item.category.name, UNIT_PIECE, quantity, float(item.price), key in purchased
                )
            )
        for name, (quantity, price) in counts.custom.items():
            key = f"custom:{name}"[:120]
            section.add(ShoppingLine(key, name, "Pieza propia", UNIT_PIECE, quantity, price, key in purchased))
        return section

    def _addon_section(self, counts: ShoppingVisitor, purchased: set[str]) -> ShoppingSection:
        section = ShoppingSection("addons", "Complementos")
        addons = {addon.slug: addon for addon in self.addons.list_all()}
        for slug, quantity in counts.addons.items():
            addon = addons.get(slug)
            if addon is None:
                continue
            key = f"addon:{slug}"
            section.add(
                ShoppingLine(
                    key, addon.name, addon.description, UNIT_PIECE, quantity, float(addon.price), key in purchased
                )
            )
        return section

    def _finish_section(self, counts: ShoppingVisitor, purchased: set[str]) -> ShoppingSection:
        section = ShoppingSection("finishes", "Acabados")
        materials = {material.slug: material for material in self.materials.list_by_surface()}
        for (surface, slug), area in counts.surfaces.items():
            material = materials.get(slug)
            if material is None:
                continue
            key = f"material:{surface}:{slug}"
            line = ShoppingLine(
                key,
                material.name,
                SURFACE_LABELS.get(surface, surface),
                UNIT_AREA,
                round(area, 2),
                float(material.price_per_unit),
                key in purchased,
            )
            section.add(line)
        return section

    @staticmethod
    def _redesign_section(redesign: Redesign, purchased: set[str]) -> ShoppingSection:
        section = ShoppingSection("redesign", "Ideas del último rediseño")
        suggestions = redesign.suggestions if isinstance(redesign.suggestions, dict) else {}
        for group, title in SUGGESTION_GROUPS.items():
            subsection = ShoppingSection(f"redesign:{group}", title)
            for index, item in enumerate(suggestions.get(group) or []):
                price = float(item.get("price") or 0)
                if price <= 0:
                    continue
                key = f"redesign:{redesign.id.hex[:8]}:{group}:{index}"
                detail = item.get("description") or title
                subsection.add(
                    ShoppingLine(key, item.get("name", title), detail, UNIT_PIECE, 1, price, key in purchased)
                )
            section.add(subsection)
        return section

    @staticmethod
    def _latest_redesign(project: Project) -> Redesign | None:
        for redesign in project.redesigns:
            if redesign.status == RedesignStatus.READY and redesign.suggestions:
                return redesign
        return None

    def _to_out(self, project: Project, root: ShoppingSection, include_redesign: bool) -> ShoppingListOut:
        lines = root.lines()
        total, purchased_total = root.total(), root.purchased_total()
        limit = float(project.budget_limit) if project.budget_limit is not None else None
        return ShoppingListOut(
            project_id=project.id,
            project_name=project.name,
            currency=self.settings.currency_code,
            include_redesign=include_redesign,
            has_redesign=self._latest_redesign(project) is not None,
            sections=[
                ShoppingSectionOut(
                    key=section.key,
                    title=section.title,
                    total=section.total(),
                    purchased_total=section.purchased_total(),
                    lines=[self._line_out(line) for line in section.lines()],
                )
                for section in root.children
            ],
            total=total,
            purchased_total=purchased_total,
            pending_total=round(total - purchased_total, 2),
            item_count=len(lines),
            purchased_count=sum(1 for line in lines if line.purchased),
            budget_limit=limit,
            budget_remaining=round(limit - total, 2) if limit else None,
            budget_used_ratio=round(total / limit, 4) if limit else None,
            budget_status=budget_status(total, limit, self.settings.shopping_budget_warning_ratio),
        )

    @staticmethod
    def _line_out(line: ShoppingLine) -> ShoppingLineOut:
        return ShoppingLineOut(
            key=line.key,
            title=line.title,
            detail=line.detail,
            unit=line.unit,
            quantity=line.quantity,
            unit_price=line.unit_price,
            total=line.total(),
            purchased=line.purchased,
        )

    def owned(self, user: User, project_id: uuid.UUID) -> Project:
        project = self.projects.get_owned(project_id, user.id)
        if project is None:
            raise ShoppingProjectNotFound
        return project
