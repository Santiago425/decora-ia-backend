import uuid

import pytest
from fastapi.testclient import TestClient

from app.patterns.composites.shopping_list import ShoppingLine, ShoppingSection, budget_status
from app.patterns.visitors.scene_visitors import ShoppingVisitor, walk_scene


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def designer(client: TestClient) -> dict:
    email = f"shopper-{uuid.uuid4().hex[:8]}@example.com"
    session = client.post(
        "/api/v1/auth/register", json={"full_name": "Compradora", "email": email, "password": "secreta123"}
    )
    return auth(session.json()["access_token"])


@pytest.fixture
def project(client: TestClient, designer: dict) -> dict:
    body = {"name": "Sala con compras", "room_type": "living_room", "style": "nordic"}
    return client.post("/api/v1/projects", json=body, headers=designer).json()


def url(project: dict, suffix: str = "") -> str:
    return f"/api/v1/projects/{project['id']}/shopping-list{suffix}"


def test_composite_adds_nested_sections_and_purchased_lines():
    root = ShoppingSection("list", "Lista")
    nested = ShoppingSection("inner", "Interna").add(ShoppingLine("b", "B", "", "unidad", 2, 50, purchased=True))
    root.add(ShoppingSection("outer", "Externa").add(ShoppingLine("a", "A", "", "m²", 1.5, 100)).add(nested))
    assert root.total() == 250
    assert root.purchased_total() == 100
    assert [line.key for line in root.lines()] == ["a", "b"]


def test_budget_status_thresholds():
    assert budget_status(100, None, 0.9) == "none"
    assert budget_status(50, 100, 0.9) == "under"
    assert budget_status(95, 100, 0.9) == "near"
    assert budget_status(101, 100, 0.9) == "over"


def test_shopping_visitor_counts_repeated_pieces_inside_groups():
    item = {"kind": "item", "furniture_id": 1, "addons": ["a"], "name": "Sofá", "price": 10}
    scene = {
        "room": {"width": 2, "length": 3, "height": 2.5, "wall_material": "w", "floor_material": "f"},
        "nodes": [item, {"kind": "group", "children": [item, {"kind": "item", "name": "Propio", "price": 7}]}],
    }
    counts = walk_scene(scene, ShoppingVisitor())
    assert counts.furniture == {1: 2}
    assert counts.addons == {"a": 2}
    assert counts.custom == {"Propio": (1, 7.0)}
    assert counts.surfaces == {("floor", "f"): 6, ("wall", "w"): 25}


def test_list_matches_the_estimated_budget(client, designer, project):
    data = client.get(url(project), headers=designer).json()
    keys = [section["key"] for section in data["sections"]]
    assert keys[0] == "furniture" and "finishes" in keys
    assert data["currency"] == "COP"
    assert data["total"] == pytest.approx(float(project["estimated_budget"]))
    assert data["budget_status"] == "none"
    assert data["item_count"] == sum(len(section["lines"]) for section in data["sections"])


def test_budget_limit_flags_when_the_design_goes_over(client, designer, project):
    total = client.get(url(project), headers=designer).json()["total"]
    over = client.put(url(project, "/budget"), json={"amount": total / 2}, headers=designer).json()
    assert over["budget_status"] == "over"
    assert over["budget_remaining"] == pytest.approx(-total / 2)
    under = client.put(url(project, "/budget"), json={"amount": total * 2}, headers=designer).json()
    assert under["budget_status"] == "under"
    cleared = client.put(url(project, "/budget"), json={"amount": None}, headers=designer).json()
    assert cleared["budget_limit"] is None and cleared["budget_status"] == "none"


def test_marking_lines_as_bought_updates_the_pending_total(client, designer, project):
    first = client.get(url(project), headers=designer).json()["sections"][0]["lines"][0]
    data = client.put(url(project, "/purchased"), json={"keys": [first["key"]]}, headers=designer).json()
    assert data["purchased_count"] == 1
    assert data["purchased_total"] == pytest.approx(first["total"])
    assert data["pending_total"] == pytest.approx(data["total"] - first["total"])


def test_export_csv_lists_every_line_and_the_total(client, designer, project):
    response = client.get(url(project, "/export?format=csv"), headers=designer)
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    rows = response.text.strip().splitlines()
    assert rows[0].lstrip("﻿").startswith("Sección,Producto")
    assert rows[-1].startswith("Total")


def test_other_users_cannot_see_the_list(client, project, user_token):
    assert client.get(url(project), headers=auth(user_token)).status_code == 404


def test_redesign_ideas_join_the_list_only_when_asked(client, designer, photo):
    data = {"room_type": "living_room", "style": "industrial", "budget": "2500000"}
    files = {"image": ("room.jpg", photo, "image/jpeg")}
    redesign = client.post("/api/v1/redesigns", headers=designer, data=data, files=files).json()
    project = {"id": redesign["project_id"]}

    base = client.get(url(project), headers=designer).json()
    assert base["has_redesign"] is True
    assert "redesign" not in [section["key"] for section in base["sections"]]

    full = client.get(url(project, "?include_redesign=true"), headers=designer).json()
    ideas = next(section for section in full["sections"] if section["key"] == "redesign")
    assert ideas["lines"] and full["total"] == pytest.approx(base["total"] + ideas["total"])
