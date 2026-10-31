import json
import re
from abc import ABC, abstractmethod

from pydantic import ValidationError

from app.patterns.ai.ai_provider import AIError
from app.patterns.ai.gemini_adapter import GeminiClient
from app.patterns.assistant.vocabulary import (
    PAGES,
    AssistantAction,
    AssistantContext,
    Interpretation,
    Vocabulary,
    contains_word,
    normalize,
)

GENERIC_WORDS = {"pintura", "piso", "pared", "porcelanato", "baldosa", "de", "con", "en"}
PAGE_WORDS = {
    "dashboard": ("inicio", "dashboard", "panel", "principal"),
    "redesign": ("rediseno", "redisenar", "foto"),
    "editor": ("editor", "3d"),
    "projects": ("proyectos", "mis proyectos"),
    "assistant": ("chat",),
    "docs": ("documentacion", "patrones", "uml"),
}


# Strategy: the assistant can understand messages with the AI or with local rules; both return the same result.
class IntentInterpreter(ABC):
    name: str

    @abstractmethod
    def interpret(self, message: str, context: AssistantContext, vocabulary: Vocabulary) -> Interpretation: ...


def _match(text: str, options: dict[str, str]) -> str | None:
    best, best_length = None, 0
    for slug, name in options.items():
        for phrase in {normalize(name), normalize(slug).replace("_", " ")}:
            candidates = {phrase, re.sub(r"(es|s)$", "", phrase)} if " " not in phrase else {phrase}
            for candidate in candidates:
                if len(candidate) > 2 and contains_word(text, candidate) and len(candidate) > best_length:
                    best, best_length = slug, len(candidate)
    return best


def _match_by_words(text: str, options: dict[str, str]) -> str | None:
    scores = {}
    for slug, name in options.items():
        words = [w for w in re.findall(r"\w+", normalize(name)) if len(w) > 3 and w not in GENERIC_WORDS]
        scores[slug] = sum(1 for word in words if contains_word(text, word))
    best = max(scores, key=scores.get, default=None)
    return best if best and scores[best] > 0 else None


def _has(text: str, *patterns: str) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


class RuleBasedInterpreter(IntentInterpreter):
    name = "rules"

    def interpret(self, message: str, context: AssistantContext, vocabulary: Vocabulary) -> Interpretation:
        text = normalize(message)
        name = context.assistant_name
        style = _match(text, vocabulary.styles)
        room = _match(text, vocabulary.room_types)

        if _has(text, r"\bdesha(z|cer|ce)\b", r"\bdevuelve\b"):
            return self._editor(context, "undo", "Listo, deshice el último cambio.")
        if _has(text, r"\breha(z|cer|ce)\b"):
            return self._editor(context, "redo", "Volví a aplicar el cambio.")

        if _has(text, r"\b(crea|crear|creame|nuevo|nueva|empezar|empieza|arma)\b") and _has(
            text, r"\b(proyecto|diseno|habitacion|espacio)\b"
        ) or (room and _has(text, r"\b(crea|crear|creame|nuevo|nueva)\b")):
            return Interpretation(
                reply="Creé tu proyecto y te llevo al editor 3D para que empieces a diseñar.",
                intent="create_project",
                actions=[AssistantAction(type="create_project", params={"room_type": room, "style": style})],
            )

        if _has(text, r"redisen", r"\bfoto\b", r"\bimagen\b"):
            budget = re.search(r"(\d[\d.]{3,})", text)
            params = {"room_type": room, "style": style}
            if budget:
                params["budget"] = float(budget.group(1).replace(".", ""))
            return Interpretation(
                reply="Te llevo a Rediseño con esas opciones. Sube o toma la foto de tu espacio y yo me encargo del resto.",
                intent="start_redesign",
                actions=[AssistantAction(type="start_redesign", params=params)],
            )

        if _has(text, r"presupuesto", r"\bcuanto\b", r"\bgast", r"\bcosto"):
            return Interpretation(reply="", intent="budget")

        editor = self._editor_request(text, context, vocabulary, style)
        if editor:
            return editor

        if _has(text, r"\b(ve|ir|abre|abrir|llevame|lleva|muestrame|vamos|quiero ver)\b"):
            for page, words in PAGE_WORDS.items():
                if any(contains_word(text, word) for word in words):
                    return Interpretation(
                        reply="¡Vamos!", intent="navigate", actions=[AssistantAction(type="navigate", params={"to": page})]
                    )

        if _has(text, r"recomiend", r"\bidea", r"consejo", r"sugier", r"que estilo"):
            return self._recommend(vocabulary, room)

        if _has(text, r"^(hola|buenas|hey|buen dia|buenos dias|buenas tardes|buenas noches)\b"):
            return Interpretation(reply=f"¡Hola! Soy {name}. {self._help(context)}", intent="greeting")

        return Interpretation(reply=f"No estoy segura de haberte entendido. {self._help(context)}", intent="help")

    def _editor_request(self, text, context, vocabulary, style) -> Interpretation | None:
        action, reply = None, ""
        if _has(text, r"\b(agrega|agregar|anade|anadir|pon|ponme|coloca|mete|incluye|quiero)\b"):
            item_name = _match_by_words(text, {str(i.id): i.name for i in vocabulary.furniture})
            category = _match(text, vocabulary.categories)
            if item_name or category:
                params = {"furniture_id": int(item_name)} if item_name else {"category": category}
                action, reply = AssistantAction(type="add_furniture", params=params), "Agregué el mueble a tu habitación."
        if not action and _has(text, r"\bpared", r"\bmuro"):
            material = _match_by_words(text, vocabulary.walls)
            if material:
                action = AssistantAction(type="change_wall", params={"material": material})
                reply = f"Cambié las paredes a {vocabulary.walls[material].lower()}."
        if not action and _has(text, r"\bpiso\b", r"\bsuelo\b"):
            material = _match_by_words(text, vocabulary.floors)
            if material:
                action = AssistantAction(type="change_floor", params={"material": material})
                reply = f"Cambié el piso a {vocabulary.floors[material].lower()}."
        if not action and style and _has(text, r"\b(estilo|cambia|aplica|usa|hazlo|ponle)\b"):
            action = AssistantAction(type="change_style", params={"style": style})
            reply = f"Apliqué el estilo {vocabulary.styles[style]}: luz, paredes y piso combinan ahora."
        if not action and _has(text, r"mas luz", r"\bilumina", r"mas clar", r"mas brillante"):
            action, reply = AssistantAction(type="set_lighting", params={"delta": 0.25}), "Subí la luz de la habitación."
        if not action and _has(text, r"menos luz", r"mas oscur", r"\btenue"):
            action, reply = AssistantAction(type="set_lighting", params={"delta": -0.25}), "Bajé la luz para un ambiente más cálido."
        if not action and _has(text, r"\b(gira|girar|rota|rotar|voltea)\b"):
            action, reply = AssistantAction(type="rotate_selected", params={"degrees": 90}), "Giré el mueble seleccionado."
        if not action and _has(text, r"\b(elimina|eliminar|quita|quitar|borra|borrar|saca)\b"):
            action, reply = AssistantAction(type="remove_selected"), "Quité el mueble seleccionado."
        if not action and _has(text, r"\b(duplica|duplicar|copia|otro igual)\b"):
            action, reply = AssistantAction(type="duplicate_selected"), "Dupliqué el mueble seleccionado."
        if not action:
            return None
        if not context.in_editor:
            return Interpretation(
                reply="Eso lo hago dentro del editor 3D. Abre un proyecto y vuelve a pedírmelo.",
                intent="needs_editor",
                actions=[AssistantAction(type="navigate", params={"to": "editor"})],
            )
        return Interpretation(reply=reply, intent=action.type, actions=[action])

    def _editor(self, context: AssistantContext, action: str, reply: str) -> Interpretation:
        if not context.in_editor:
            return Interpretation(reply="Puedo deshacer y rehacer cambios cuando estás en el editor 3D.", intent="needs_editor")
        return Interpretation(reply=reply, intent=action, actions=[AssistantAction(type=action)])

    def _recommend(self, vocabulary: Vocabulary, room: str | None) -> Interpretation:
        slugs = list(vocabulary.styles)
        if not slugs:
            return Interpretation(reply="Aún no hay estilos en el catálogo.", intent="recommend")
        offset = sum(map(ord, room or "")) % len(slugs)
        picks = [slugs[(offset + i) % len(slugs)] for i in range(min(2, len(slugs)))]
        place = f" para tu {vocabulary.room_types[room].lower()}" if room else ""
        ideas = " ".join(f"**{vocabulary.styles[s]}**: {vocabulary.style_descriptions.get(s, '')}" for s in picks)
        return Interpretation(
            reply=f"Te recomiendo estos estilos{place}. {ideas} ¿Quieres que cree un proyecto con alguno?",
            intent="recommend",
        )

    @staticmethod
    def _help(context: AssistantContext) -> str:
        if context.in_editor:
            return "Pídeme cosas como «agrega una planta», «paredes verde salvia», «estilo japandi», «más luz» o «deshaz»."
        return "Puedo crear un proyecto («crea una sala nórdica»), llevarte a rediseñar una foto, recomendarte estilos o decirte tu presupuesto."


PROMPT = """You are {name}, the interior design assistant of the Habita app. Always answer in warm, brief Spanish (max 3 sentences).
You can trigger app actions. Return ONLY JSON: {{"reply": str, "intent": str, "actions": [{{"type": str, "params": object}}]}}.
Available actions:
- navigate {{"to": one of {pages}}}
- create_project {{"room_type": slug, "style": slug, "name": optional str}}
- start_redesign {{"room_type": optional slug, "style": optional slug, "budget": optional number}}
{editor_actions}
Use only slugs and ids listed below. Use no action when the user just chats or asks for advice.
Catalog:
styles = {styles}
room_types = {room_types}
furniture (id, name, category) = {furniture}
wall_materials = {walls}
floor_materials = {floors}
User status: page="{page}", open project={project}, projects={count}, total estimated budget={budget} {currency}.
Recent conversation:
{history}
User message: {message}"""

EDITOR_ACTIONS_PROMPT = """- add_furniture {"furniture_id": id} or {"category": slug}
- change_style {"style": slug}
- change_wall {"material": slug}, change_floor {"material": slug}
- set_lighting {"delta": number between -1 and 1}
- undo, redo, rotate_selected {"degrees": number}, remove_selected, duplicate_selected"""


class GeminiIntentInterpreter(IntentInterpreter):
    name = "gemini"

    def __init__(self, client: GeminiClient, model: str, currency: str) -> None:
        self.client = client
        self.model = model
        self.currency = currency

    def interpret(self, message: str, context: AssistantContext, vocabulary: Vocabulary) -> Interpretation:
        prompt = PROMPT.format(
            name=context.assistant_name,
            pages=list(PAGES),
            editor_actions=EDITOR_ACTIONS_PROMPT if context.in_editor else "(editor actions are only available inside the 3D editor)",
            styles=vocabulary.styles,
            room_types=vocabulary.room_types,
            furniture=[(item.id, item.name, item.category) for item in vocabulary.furniture],
            walls=vocabulary.walls,
            floors=vocabulary.floors,
            page=context.page,
            project=context.project_name or "none",
            count=context.project_count,
            budget=round(context.total_budget),
            currency=self.currency,
            history="\n".join(f"{sender}: {text}" for sender, text in context.history) or "(empty)",
            message=message,
        )
        parts = self.client.generate(self.model, [{"text": prompt}], {"responseMimeType": "application/json", "temperature": 0.4})
        text = "".join(part.get("text", "") for part in parts)
        try:
            return Interpretation.model_validate(json.loads(text))
        except (json.JSONDecodeError, ValidationError):
            raise AIError("La IA respondió en un formato inesperado") from None


# Chain of Responsibility: if the AI fails (quota, network, bad answer) the local rules answer instead.
class FallbackInterpreter(IntentInterpreter):
    def __init__(self, primary: IntentInterpreter, fallback: IntentInterpreter) -> None:
        self.primary = primary
        self.fallback = fallback
        self.name = primary.name

    def interpret(self, message: str, context: AssistantContext, vocabulary: Vocabulary) -> Interpretation:
        try:
            return self.primary.interpret(message, context, vocabulary)
        except AIError:
            return self.fallback.interpret(message, context, vocabulary)
