from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import get_settings
from app.patterns.singleton import SingletonMeta


class Database(metaclass=SingletonMeta):
    def __init__(self) -> None:
        settings = get_settings()
        connect_args = {"check_same_thread": False} if settings.is_sqlite else {}
        self.engine: Engine = create_engine(
            settings.database_url,
            echo=settings.database_echo,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)

    def session(self) -> Session:
        return self.session_factory()


def get_db() -> Iterator[Session]:
    session = Database().session()
    try:
        yield session
    finally:
        session.close()
