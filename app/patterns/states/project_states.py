from __future__ import annotations

from app.models import Project, ProjectStatus


class ProjectTransitionError(Exception):
    def __init__(self, user_message: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message


# State: the project's stage decides whether it can be edited and which stage comes next.
class ProjectState:
    status: ProjectStatus
    actions: tuple[str, ...] = ()

    def edit(self, lifecycle: ProjectLifecycle) -> None:
        pass

    def start(self, lifecycle: ProjectLifecycle) -> None:
        raise ProjectTransitionError("El proyecto ya está en diseño")

    def finish(self, lifecycle: ProjectLifecycle) -> None:
        raise ProjectTransitionError("Solo puedes terminar un proyecto que esté en diseño")

    def reopen(self, lifecycle: ProjectLifecycle) -> None:
        raise ProjectTransitionError("Solo puedes reabrir un proyecto terminado")


class DraftState(ProjectState):
    status = ProjectStatus.DRAFT
    actions = ("start",)

    def edit(self, lifecycle):
        lifecycle.transition_to(InDesignState())

    def start(self, lifecycle):
        lifecycle.transition_to(InDesignState())


class InDesignState(ProjectState):
    status = ProjectStatus.IN_DESIGN
    actions = ("finish",)

    def finish(self, lifecycle):
        lifecycle.transition_to(FinishedState())


class FinishedState(ProjectState):
    status = ProjectStatus.FINISHED
    actions = ("reopen",)

    def edit(self, lifecycle):
        raise ProjectTransitionError("Este proyecto está terminado. Reábrelo para seguir editando")

    def reopen(self, lifecycle):
        lifecycle.transition_to(InDesignState())


STATES = {state.status: state for state in (DraftState(), InDesignState(), FinishedState())}


class ProjectLifecycle:
    def __init__(self, project: Project) -> None:
        self.project = project
        self.state = STATES[project.status or ProjectStatus.DRAFT]

    @property
    def actions(self) -> list[str]:
        return list(self.state.actions)

    def transition_to(self, state: ProjectState) -> None:
        self.state = state
        self.project.status = state.status

    def edit(self) -> None:
        self.state.edit(self)

    def apply(self, action: str) -> None:
        handlers = {"start": self.state.start, "finish": self.state.finish, "reopen": self.state.reopen}
        if action not in handlers:
            raise ProjectTransitionError("Acción no válida para el proyecto")
        handlers[action](self)
