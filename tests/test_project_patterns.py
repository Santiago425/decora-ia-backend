from types import SimpleNamespace

import pytest

from app.models import Project, ProjectStatus
from app.patterns.builders.room_builder import RoomBuilder, StarterLayoutDirector
from app.patterns.mementos.scene_memento import ProjectSceneOriginator
from app.patterns.prototypes.project_prototype import ProjectPrototype
from app.patterns.states.project_states import ProjectLifecycle, ProjectTransitionError
from app.patterns.visitors.scene_visitors import BudgetVisitor, walk_scene


def furniture(item_id, shape, width=1.0, depth=0.5, price=100):
    category = SimpleNamespace(slug=shape, shape=shape)
    return SimpleNamespace(
        id=item_id, name=shape, category=category, width=width, depth=depth, height=1.0, default_color="#aaaaaa", price=price
    )


def test_room_builder_produces_a_complete_scene():
    scene = RoomBuilder(4, 3, 2.5).with_walls("wall_a").with_floor("floor_a").with_lighting("#ffffff", 1.2).build()
    assert scene["room"] == {"width": 4, "length": 3, "height": 2.5, "wall_material": "wall_a", "floor_material": "floor_a"}
    assert scene["lighting"] == {"color": "#ffffff", "intensity": 1.2}
    assert scene["nodes"] == []


def test_director_places_anchors_against_the_walls():
    builder = RoomBuilder(4, 3, 2.5)
    StarterLayoutDirector(builder).furnish([furniture(1, "sofa", depth=0.9), furniture(2, "shelf"), furniture(3, "rug")])
    nodes = {node["shape"]: node for node in builder.build()["nodes"]}
    assert nodes["sofa"]["position"] == [0, pytest.approx(-1.5 + 0.45 + 0.05)]
    assert nodes["shelf"]["rotation"] == 90
    assert nodes["rug"]["position"] == [0, 0.2]


def test_budget_visitor_walks_groups():
    scene = {
        "room": {"width": 2, "length": 2, "height": 2, "wall_material": "w", "floor_material": "f"},
        "nodes": [
            {"kind": "item", "furniture_id": 1, "addons": ["a"]},
            {"kind": "group", "children": [{"kind": "item", "furniture_id": 2, "addons": []}]},
        ],
    }
    visitor = walk_scene(scene, BudgetVisitor({1: 100, 2: 50}, {"w": 1, "f": 10}, {"a": 5}))
    assert visitor.total == 100 + 5 + 50 + 4 * 10 + 16 * 1


def test_project_lifecycle_moves_through_its_states():
    project = Project(status=ProjectStatus.DRAFT)
    lifecycle = ProjectLifecycle(project)
    lifecycle.edit()
    assert project.status == ProjectStatus.IN_DESIGN
    lifecycle.apply("finish")
    with pytest.raises(ProjectTransitionError):
        lifecycle.edit()
    lifecycle.apply("reopen")
    assert project.status == ProjectStatus.IN_DESIGN


def test_memento_restores_a_snapshot_without_sharing_references():
    project = Project(scene={"nodes": [{"id": "a"}]}, estimated_budget=10)
    originator = ProjectSceneOriginator(project)
    memento = originator.create_memento("v1")
    project.scene["nodes"].append({"id": "b"})
    project.estimated_budget = 99
    originator.restore(memento)
    assert project.scene == {"nodes": [{"id": "a"}]}
    assert project.estimated_budget == 10


def test_prototype_clone_gets_new_node_ids():
    original = Project(name="Sala", status=ProjectStatus.FINISHED, scene={"nodes": [{"id": "a", "children": [{"id": "b"}]}]})
    copy = ProjectPrototype(original).clone("Sala 2")
    assert copy.status == ProjectStatus.DRAFT
    assert copy.scene["nodes"][0]["id"] != "a"
    assert copy.scene["nodes"][0]["children"][0]["id"] != "b"
    assert original.scene["nodes"][0]["id"] == "a"
