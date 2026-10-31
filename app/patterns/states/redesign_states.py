from __future__ import annotations

from app.models import Redesign, RedesignStatus


class InvalidTransition(Exception):
    pass


# State: each stage of a redesign decides which stage can come next.
class RedesignState:
    status: RedesignStatus

    def start_processing(self, process: RedesignProcess) -> None:
        raise InvalidTransition(f"Cannot process from {self.status.value}")

    def complete(self, process: RedesignProcess, result_url: str) -> None:
        raise InvalidTransition(f"Cannot complete from {self.status.value}")

    def fail(self, process: RedesignProcess, message: str) -> None:
        process.redesign.error_message = message[:300]
        process.transition_to(ErrorState())


class UploadingState(RedesignState):
    status = RedesignStatus.UPLOADING

    def start_processing(self, process):
        process.transition_to(ProcessingState())


class ProcessingState(RedesignState):
    status = RedesignStatus.PROCESSING

    def complete(self, process, result_url):
        process.redesign.result_image_url = result_url
        process.redesign.error_message = None
        process.transition_to(ReadyState())


class ReadyState(RedesignState):
    status = RedesignStatus.READY

    def fail(self, process, message):
        raise InvalidTransition("A finished redesign cannot fail")


class ErrorState(RedesignState):
    status = RedesignStatus.ERROR

    def start_processing(self, process):
        process.transition_to(ProcessingState())


STATES = {state.status: state for state in (UploadingState(), ProcessingState(), ReadyState(), ErrorState())}


class RedesignProcess:
    def __init__(self, redesign: Redesign) -> None:
        self.redesign = redesign
        self.state = STATES[redesign.status or RedesignStatus.UPLOADING]
        redesign.status = self.state.status

    def transition_to(self, state: RedesignState) -> None:
        self.state = state
        self.redesign.status = state.status

    def start_processing(self) -> None:
        self.state.start_processing(self)

    def complete(self, result_url: str) -> None:
        self.state.complete(self, result_url)

    def fail(self, message: str) -> None:
        self.state.fail(self, message)
