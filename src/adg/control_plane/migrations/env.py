from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from adg.app.settings import get_settings
from adg.control_plane.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Resolve the database URL from environment-backed settings or Alembic config."""

    settings = get_settings()
    if "control_plane_database_url" in settings.model_fields_set:
        return settings.control_plane_database_url

    configured = config.get_main_option("sqlalchemy.url")
    if configured:
        return configured
    return settings.control_plane_database_url


def run_migrations_offline() -> None:
    """Run Alembic migrations without creating an engine."""

    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run Alembic migrations through a live database connection."""

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
