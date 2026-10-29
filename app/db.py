from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row
from .settings import DATABASE_URL

@contextmanager
def connection(identity=None):
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.transaction():
            if identity is not None:
                conn.execute("SELECT set_config('app.tenant_id', %s, true)", (str(identity["tenant_id"]),))
                conn.execute("SELECT set_config('app.user_id', %s, true)", (str(identity["user_id"]),))
                conn.execute("SELECT set_config('app.role', %s, true)", (identity["role"],))
            yield conn
