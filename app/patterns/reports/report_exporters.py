import csv
import io
from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import datetime
from typing import Any, ClassVar

from app.models import User
from app.repositories import ProjectRepository, UserRepository


# Template Method: export() fixes the steps (columns, rows, format, file name); each report fills in its own.
class ReportExporter(ABC):
    slug: str
    title: str

    def export(self) -> tuple[str, str]:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(self.columns())
        for record in self.records():
            writer.writerow([self.format_value(value) for value in self.to_row(record)])
        return self.file_name(), "﻿" + buffer.getvalue()

    def file_name(self) -> str:
        return f"habita-{self.slug}-{datetime.now().strftime('%Y%m%d')}.csv"

    @staticmethod
    def format_value(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M")
        if isinstance(value, bool):
            return "Sí" if value else "No"
        return str(value)

    @abstractmethod
    def columns(self) -> list[str]: ...

    @abstractmethod
    def records(self) -> Iterable[Any]: ...

    @abstractmethod
    def to_row(self, record: Any) -> list[Any]: ...


class UsersReport(ReportExporter):
    slug = "usuarios"
    title = "Usuarios"

    def __init__(self, users: UserRepository) -> None:
        self.users = users

    def columns(self) -> list[str]:
        return ["Nombre", "Correo", "Rol", "Activo", "Proyectos", "Último ingreso", "Registro"]

    def records(self) -> Iterable[tuple[User, int]]:
        return self.users.all_with_project_counts()

    def to_row(self, record: tuple[User, int]) -> list[Any]:
        user, projects = record
        role = "Administrador" if user.role.value == "admin" else "Usuario"
        return [user.full_name, user.email, role, user.is_active, projects, user.last_login_at, user.created_at]


class ProjectsReport(ReportExporter):
    slug = "proyectos"
    title = "Proyectos"
    STATUS: ClassVar[dict[str, str]] = {"draft": "Borrador", "in_design": "En diseño", "finished": "Terminado"}

    def __init__(self, projects: ProjectRepository) -> None:
        self.projects = projects

    def columns(self) -> list[str]:
        return ["Proyecto", "Dueño", "Estado", "Habitación", "Estilo", "Presupuesto", "Rediseños", "Actualizado"]

    def records(self):
        return self.projects.list_all_with_owner()

    def to_row(self, project) -> list[Any]:
        return [
            project.name,
            project.owner.email,
            self.STATUS[project.status.value],
            project.room_type.name if project.room_type else None,
            project.style.name if project.style else None,
            project.estimated_budget,
            len(project.redesigns),
            project.updated_at,
        ]


def report_for(kind: str, users: UserRepository, projects: ProjectRepository) -> ReportExporter | None:
    reports = {UsersReport.slug: lambda: UsersReport(users), ProjectsReport.slug: lambda: ProjectsReport(projects)}
    factory = reports.get(kind)
    return factory() if factory else None
