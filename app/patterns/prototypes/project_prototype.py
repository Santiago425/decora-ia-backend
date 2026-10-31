from copy import deepcopy

from app.models import Project, ProjectStatus
from app.patterns.builders.room_builder import new_node_id


def _renew_ids(nodes: list[dict]) -> list[dict]:
    for node in nodes:
        node["id"] = new_node_id()
        _renew_ids(node.get("children", []))
    return nodes


# Prototype: a new project is created by copying an existing one instead of building it from scratch.
class ProjectPrototype:
    def __init__(self, project: Project) -> None:
        self.project = project

    def clone(self, name: str) -> Project:
        scene = deepcopy(self.project.scene) if self.project.scene else None
        if scene:
            _renew_ids(scene.get("nodes", []))
        return Project(
            user_id=self.project.user_id,
            room_type_id=self.project.room_type_id,
            style_id=self.project.style_id,
            name=name,
            status=ProjectStatus.DRAFT,
            estimated_budget=self.project.estimated_budget,
            scene=scene,
        )
