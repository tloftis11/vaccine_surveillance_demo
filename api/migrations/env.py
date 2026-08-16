from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------------
# Make the project root importable so that "from api.db import Base" works
# whether Alembic is run from inside the api/ directory or from the repo root.
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent          # …/api/migrations
API_DIR = HERE.parent                           # …/api
PROJECT_ROOT = API_DIR.parent                   # …/vaccine-surveillance

for p in (str(PROJECT_ROOT), str(API_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Skip migration entirely during build phase (DATABASE_URL not yet injected)
if not os.environ.get("DATABASE_URL"):
    print("DATABASE_URL not set — skipping migration (will run at startup)")
    sys.exit(0)

# Import Base (and all models so metadata is complete)
from db import Base  # noqa: E402
import models  # noqa: F401, E402  -- registers all ORM models with Base

# ---------------------------------------------------------------------------
# Alembic Config object — gives access to the .ini file values
# ---------------------------------------------------------------------------
config = context.config

# Override sqlalchemy.url from the environment variable if set
db_url = os.environ.get("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# Interpret the config file for Python logging if present
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Run migrations
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.  Calls to
    context.execute() emit the given string to the script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a connection
    with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
