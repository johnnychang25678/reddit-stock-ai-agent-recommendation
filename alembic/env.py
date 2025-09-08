from logging.config import fileConfig
from typing import Any
from dotenv import load_dotenv

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from stock_ai.db.base import Base
import stock_ai.db.models

import os

load_dotenv()  # take environment variables from .env

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def _get_database_url() -> str:
    target = os.getenv("DB_TARGET", "LOCAL").upper()
    if target == "REMOTE":
        url = os.getenv("DATABASE_URL_REMOTE")
    else:
        url = os.getenv("DATABASE_URL_LOCAL")

    if not url:
        # Fallback to alembic.ini if nothing in .env
        url = config.get_main_option("sqlalchemy.url")

    if not url:
        raise RuntimeError(
            "No database URL found. Set DATABASE_URL_LOCAL/REMOTE in .env or sqlalchemy.url in alembic.ini"
        )
    return url



# ---- Exclude Supabase-managed schemas from autogenerate ----
# These schemas are owned by Supabase.
_SKIP_SCHEMAS = {
    "auth",
    "storage",
    "realtime",
    "pgbouncer",
    "pg_catalog",
    "information_schema",
    "extensions",
    "supabase_functions",
    "supabase_migrations",
}


def include_object(
    obj: Any, name: str, type_: str, reflected: bool, compare_to: Any
) -> bool:
    schema = getattr(obj, "schema", None)
    if schema in _SKIP_SCHEMAS:
        return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    context.configure(
        url=_get_database_url(),
        target_metadata=target_metadata,
        include_object=include_object,
        compare_server_default=True,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Inject URL into alembic config at runtime
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = _get_database_url()

    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    # alembic default is online mode (writes to DB directly)
    run_migrations_online()
