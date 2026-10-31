from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Base

ModelT = TypeVar("ModelT", bound=Base)


# Repository: services work with collections of entities and never write SQL themselves.
class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, entity_id: Any) -> ModelT | None:
        return self.session.get(self.model, entity_id)

    def list(self) -> list[ModelT]:
        return list(self.session.scalars(select(self.model)))

    def count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(self.model)) or 0

    def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity

    def save(self, entity: ModelT) -> ModelT:
        return self.add(entity)

    def delete(self, entity: ModelT) -> None:
        self.session.delete(entity)
        self.session.commit()
