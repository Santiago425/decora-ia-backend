from app.patterns.assistant.vocabulary import (
    ACTION_TYPES,
    EDITOR_ACTIONS,
    PAGES,
    AssistantAction,
    AssistantContext,
    Interpretation,
    Vocabulary,
)

MAX_LIGHT_DELTA = 1.0


def _known(value, options: dict[str, str]) -> str | None:
    return value if isinstance(value, str) and value in options else None


# Whatever the interpreter says (AI or rules), only actions that exist in the catalog reach the frontend.
def sanitize(interpretation: Interpretation, context: AssistantContext, vocabulary: Vocabulary) -> Interpretation:
    clean: list[AssistantAction] = []
    for action in interpretation.actions:
        params = action.params or {}
        if action.type not in ACTION_TYPES:
            continue
        if action.type in EDITOR_ACTIONS and not context.in_editor:
            continue
        match action.type:
            case "navigate":
                if _known(params.get("to"), PAGES):
                    clean.append(AssistantAction(type="navigate", params={"to": params["to"]}))
            case "create_project":
                room = _known(params.get("room_type"), vocabulary.room_types) or next(iter(vocabulary.room_types), None)
                style = _known(params.get("style"), vocabulary.styles) or next(iter(vocabulary.styles), None)
                if room and style:
                    name = str(params.get("name") or f"{vocabulary.room_types[room]} {vocabulary.styles[style]}")[:120]
                    clean.append(AssistantAction(type="create_project", params={"room_type": room, "style": style, "name": name}))
            case "start_redesign":
                result = {
                    "room_type": _known(params.get("room_type"), vocabulary.room_types),
                    "style": _known(params.get("style"), vocabulary.styles),
                }
                budget = params.get("budget")
                if isinstance(budget, int | float) and budget > 0:
                    result["budget"] = float(budget)
                clean.append(AssistantAction(type="start_redesign", params={k: v for k, v in result.items() if v}))
            case "add_furniture":
                item = None
                if isinstance(params.get("furniture_id"), int):
                    item = vocabulary.furniture_by_id(params["furniture_id"])
                if item is None and _known(params.get("category"), vocabulary.categories):
                    item = vocabulary.cheapest_in(params["category"])
                if item:
                    clean.append(AssistantAction(type="add_furniture", params={"furniture_id": item.id, "name": item.name}))
            case "change_style":
                if _known(params.get("style"), vocabulary.styles):
                    clean.append(AssistantAction(type="change_style", params={"style": params["style"]}))
            case "change_wall" | "change_floor":
                options = vocabulary.walls if action.type == "change_wall" else vocabulary.floors
                if _known(params.get("material"), options):
                    clean.append(AssistantAction(type=action.type, params={"material": params["material"]}))
            case "set_lighting":
                delta = params.get("delta")
                if isinstance(delta, int | float) and delta != 0:
                    delta = max(-MAX_LIGHT_DELTA, min(MAX_LIGHT_DELTA, float(delta)))
                    clean.append(AssistantAction(type="set_lighting", params={"delta": delta}))
            case "rotate_selected":
                degrees = params.get("degrees", 90)
                degrees = degrees if isinstance(degrees, int | float) and -360 <= degrees <= 360 else 90
                clean.append(AssistantAction(type="rotate_selected", params={"degrees": degrees}))
            case _:
                clean.append(AssistantAction(type=action.type, params={}))
    return interpretation.model_copy(update={"actions": clean})
