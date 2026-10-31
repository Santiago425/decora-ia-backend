from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal

from app.models import Project, SceneVersion


@dataclass(frozen=True)
class SceneMemento:
    label: str
    scene: dict
    estimated_budget: Decimal


# Memento: the project saves a snapshot of its scene and can go back to it without exposing how it is stored.
class ProjectSceneOriginator:
    def __init__(self, project: Project) -> None:
        self.project = project

    def create_memento(self, label: str) -> SceneMemento:
        return SceneMemento(label, deepcopy(self.project.scene or {}), self.project.estimated_budget)

    def restore(self, memento: SceneMemento) -> None:
        self.project.scene = deepcopy(memento.scene)
        self.project.estimated_budget = memento.estimated_budget

    @staticmethod
    def to_version(project: Project, memento: SceneMemento) -> SceneVersion:
        scene = {**memento.scene, "estimated_budget": float(memento.estimated_budget)}
        return SceneVersion(project_id=project.id, label=memento.label, scene=scene)

    @staticmethod
    def from_version(version: SceneVersion) -> SceneMemento:
        scene = dict(version.scene)
        budget = Decimal(str(scene.pop("estimated_budget", 0)))
        return SceneMemento(version.label, scene, budget)
