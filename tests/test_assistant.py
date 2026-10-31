import uuid

import pytest
from fastapi.testclient import TestClient

from app.patterns.ai.ai_provider import AIError
from app.patterns.assistant.action_sanitizer import sanitize
from app.patterns.assistant.interpreters import FallbackInterpreter, IntentInterpreter, RuleBasedInterpreter
from app.patterns.assistant.vocabulary import (
    AssistantAction,
    AssistantContext,
    CatalogFurniture,
    Interpretation,
    Vocabulary,
)

VOCABULARY = Vocabulary(
    styles={"nordic": "Nórdico", "japandi": "Japandi"},
    style_descriptions={"nordic": "Madera clara.", "japandi": "Calma japonesa."},
    room_types={"living_room": "Sala", "bedroom": "Dormitorio"},
    categories={"plant": "Plantas", "sofa": "Sofás"},
    furniture=[
        CatalogFurniture(1, "Monstera en maceta", "plant", 180000),
        CatalogFurniture(2, "Olivo pequeño", "plant", 220000),
        CatalogFurniture(3, "Sofá Oslo 3 puestos", "sofa", 2890000),
    ],
    walls={"wall_sage_green": "Pintura verde salvia", "wall_terracotta": "Pintura terracota"},
    floors={"floor_walnut": "Madera nogal", "floor_microcement": "Microcemento"},
)
EDITOR = AssistantContext(assistant_name="Lumi", page="editor", project_name="Sala")
HOME = AssistantContext(assistant_name="Lumi", page="dashboard")


def understand(message: str, context: AssistantContext = EDITOR) -> Interpretation:
    return sanitize(RuleBasedInterpreter().interpret(message, context, VOCABULARY), context, VOCABULARY)


@pytest.mark.parametrize(
    ("message", "action", "params"),
    [
        ("Agrega una planta", "add_furniture", {"furniture_id": 1, "name": "Monstera en maceta"}),
        ("pon el olivo pequeño", "add_furniture", {"furniture_id": 2, "name": "Olivo pequeño"}),
        ("pinta las paredes verde salvia", "change_wall", {"material": "wall_sage_green"}),
        ("quiero el piso de microcemento", "change_floor", {"material": "floor_microcement"}),
        ("cambia al estilo japandi", "change_style", {"style": "japandi"}),
        ("necesito más luz", "set_lighting", {"delta": 0.25}),
        ("deshaz eso", "undo", {}),
        ("gira el sofá", "rotate_selected", {"degrees": 90}),
    ],
)
def test_rules_understand_editor_requests(message, action, params):
    result = understand(message)
    assert [a.type for a in result.actions] == [action]
    assert result.actions[0].params == params
    assert result.reply


def test_rules_create_projects_with_catalog_slugs():
    result = understand("Créame un dormitorio nórdico", HOME)
    assert result.actions[0].type == "create_project"
    assert result.actions[0].params == {"room_type": "bedroom", "style": "nordic", "name": "Dormitorio Nórdico"}


def test_sala_is_not_confused_with_salvia():
    assert understand("paredes verde salvia", HOME).actions[0].params == {"to": "editor"}


def test_editor_actions_are_blocked_outside_the_editor():
    result = understand("agrega una planta", HOME)
    assert result.intent == "needs_editor"
    assert [a.type for a in result.actions] == ["navigate"]


def test_sanitizer_drops_unknown_slugs_and_actions():
    raw = Interpretation(
        reply="ok",
        actions=[
            AssistantAction(type="change_style", params={"style": "gothic"}),
            AssistantAction(type="delete_database"),
            AssistantAction(type="set_lighting", params={"delta": 9}),
            AssistantAction(type="navigate", params={"to": "docs"}),
        ],
    )
    clean = sanitize(raw, EDITOR, VOCABULARY)
    assert [(a.type, a.params) for a in clean.actions] == [("set_lighting", {"delta": 1.0}), ("navigate", {"to": "docs"})]


def test_fallback_uses_rules_when_the_ai_fails():
    class BrokenAI(IntentInterpreter):
        name = "gemini"

        def interpret(self, message, context, vocabulary):
            raise AIError("quota")

    result = FallbackInterpreter(BrokenAI(), RuleBasedInterpreter()).interpret("más luz", EDITOR, VOCABULARY)
    assert result.actions[0].type == "set_lighting"


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def member(client: TestClient) -> dict:
    email = f"lumi-{uuid.uuid4().hex[:8]}@example.com"
    session = client.post("/api/v1/auth/register", json={"full_name": "Ana", "email": email, "password": "secreta123"})
    return auth(session.json()["access_token"])


def test_chat_creates_a_project_and_keeps_history(client: TestClient, member: dict):
    response = client.post("/api/v1/assistant/messages", json={"message": "crea una sala japandi"}, headers=member)
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "rules"
    action = body["reply"]["actions"][0]
    assert action["type"] == "open_project"
    project = client.get(f"/api/v1/projects/{action['params']['project_id']}", headers=member).json()
    assert project["style"]["slug"] == "japandi"

    budget = client.post("/api/v1/assistant/messages", json={"message": "¿cuánto es mi presupuesto?"}, headers=member).json()
    assert "1 proyecto" in budget["reply"]["content"]

    history = client.get("/api/v1/assistant/messages", headers=member).json()
    assert [m["sender"] for m in history] == ["user", "assistant", "user", "assistant"]
    assert client.delete("/api/v1/assistant/messages", headers=member).status_code == 200
    assert client.get("/api/v1/assistant/messages", headers=member).json() == []


def test_editor_actions_need_an_owned_project(client: TestClient, member: dict, user_token: str):
    demo_project = client.get("/api/v1/projects", headers=auth(user_token)).json()[0]["id"]
    body = {"message": "agrega una planta", "page": "editor", "project_id": demo_project}
    stranger = client.post("/api/v1/assistant/messages", json=body, headers=member).json()
    assert stranger["reply"]["intent"] == "needs_editor"
    owner = client.post("/api/v1/assistant/messages", json=body, headers=auth(user_token)).json()
    assert owner["reply"]["actions"][0]["type"] == "add_furniture"


def test_chat_requires_a_session(client: TestClient):
    assert client.post("/api/v1/assistant/messages", json={"message": "hola"}).status_code == 401
