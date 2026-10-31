
from app.core.settings import Settings
from app.models import ChatMessage, User
from app.patterns.assistant.action_sanitizer import sanitize
from app.patterns.assistant.interpreters import IntentInterpreter
from app.patterns.assistant.vocabulary import (
    AssistantAction,
    AssistantContext,
    CatalogFurniture,
    Interpretation,
    Vocabulary,
)
from app.repositories import (
    ChatMessageRepository,
    FurnitureCategoryRepository,
    FurnitureRepository,
    MaterialRepository,
    ProjectRepository,
    RoomTypeRepository,
    StyleRepository,
)
from app.schemas.assistant import ActionResponse, AssistantReply, AssistantRequest, ChatMessageResponse
from app.schemas.project import ProjectCreate
from app.services.project_service import ProjectService


class AssistantService:
    def __init__(
        self,
        messages: ChatMessageRepository,
        projects: ProjectRepository,
        project_service: ProjectService,
        styles: StyleRepository,
        room_types: RoomTypeRepository,
        categories: FurnitureCategoryRepository,
        furniture: FurnitureRepository,
        materials: MaterialRepository,
        interpreter: IntentInterpreter,
        settings: Settings,
    ) -> None:
        self.messages = messages
        self.projects = projects
        self.project_service = project_service
        self.styles = styles
        self.room_types = room_types
        self.categories = categories
        self.furniture = furniture
        self.materials = materials
        self.interpreter = interpreter
        self.settings = settings

    def history(self, user: User) -> list[ChatMessageResponse]:
        return [self._response(m) for m in self.messages.recent_by_user(user.id, self.settings.assistant_history_limit)]

    def clear(self, user: User) -> None:
        self.messages.delete_by_user(user.id)

    def send(self, user: User, request: AssistantRequest) -> AssistantReply:
        context = self._context(user, request)
        vocabulary = self._vocabulary()
        message = self.messages.add(ChatMessage(user_id=user.id, sender="user", content=request.message.strip()))

        interpretation = sanitize(self.interpreter.interpret(request.message, context, vocabulary), context, vocabulary)
        interpretation = self._run_server_actions(user, interpretation, context)

        reply = self.messages.add(
            ChatMessage(
                user_id=user.id,
                sender="assistant",
                content=interpretation.reply,
                intent=interpretation.intent,
                payload={"actions": [action.model_dump() for action in interpretation.actions]},
            )
        )
        return AssistantReply(message=self._response(message), reply=self._response(reply), provider=self.interpreter.name)

    def _run_server_actions(self, user: User, interpretation: Interpretation, context: AssistantContext) -> Interpretation:
        actions: list[AssistantAction] = []
        reply = interpretation.reply
        for action in interpretation.actions:
            if action.type == "create_project":
                project = self.project_service.create(user, ProjectCreate(**action.params, furnished=True))
                actions.append(AssistantAction(type="open_project", params={"project_id": str(project.id)}))
                reply = reply or f"Creé «{project.name}». Te llevo al editor 3D."
            else:
                actions.append(action)
        if interpretation.intent == "budget" or not reply:
            reply = reply or self._budget_reply(context)
        return interpretation.model_copy(update={"actions": actions, "reply": reply})

    def _budget_reply(self, context: AssistantContext) -> str:
        if not context.project_count:
            return "Todavía no tienes proyectos. Crea uno y te digo cuánto costaría."
        total = f"{context.total_budget:,.0f}".replace(",", ".")
        plural = "proyecto" if context.project_count == 1 else "proyectos"
        return f"Tienes {context.project_count} {plural} con un presupuesto estimado total de {total} {self.settings.currency_code}."

    def _context(self, user: User, request: AssistantRequest) -> AssistantContext:
        project_name = None
        if request.page == "editor" and request.project_id:
            project = self.projects.get_owned(request.project_id, user.id)
            project_name = project.name if project else None
        recent = self.messages.recent_by_user(user.id, self.settings.assistant_context_messages)
        return AssistantContext(
            assistant_name=self.settings.assistant_name,
            page=request.page,
            project_name=project_name,
            project_count=self.projects.count_by_user(user.id),
            total_budget=float(self.projects.total_budget_by_user(user.id)),
            history=[(m.sender, m.content) for m in recent],
        )

    def _vocabulary(self) -> Vocabulary:
        styles = self.styles.list_active()
        materials = self.materials.list_by_surface()
        return Vocabulary(
            styles={s.slug: s.name for s in styles},
            style_descriptions={s.slug: s.description for s in styles},
            room_types={r.slug: r.name for r in self.room_types.list_active()},
            categories={c.slug: c.name for c in self.categories.list_ordered()},
            furniture=[
                CatalogFurniture(i.id, i.name, i.category.slug, float(i.price)) for i in self.furniture.list_active()
            ],
            walls={m.slug: m.name for m in materials if m.surface == "wall"},
            floors={m.slug: m.name for m in materials if m.surface == "floor"},
        )

    @staticmethod
    def _response(message: ChatMessage) -> ChatMessageResponse:
        actions = (message.payload or {}).get("actions", [])
        return ChatMessageResponse(
            id=message.id,
            sender=message.sender,
            content=message.content,
            intent=message.intent,
            actions=[ActionResponse(**action) for action in actions],
            created_at=message.created_at,
        )
