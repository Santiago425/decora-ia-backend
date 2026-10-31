from logging.config import fileConfig

from alembic import context

from app.core.database import Database
from app.models import Base

if context.config.config_file_name:
    fileConfig(context.config.config_file_name)

target_metadata = Base.metadata


def run_migrations() -> None:
    engine = Database().engine
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=engine.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations()
