import os
from alembic import context
from sqlalchemy import create_engine, pool

config = context.config
url = os.environ.get("ADMIN_DATABASE_URL", config.get_main_option("sqlalchemy.url"))

def run_migrations_online():
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()

run_migrations_online()
