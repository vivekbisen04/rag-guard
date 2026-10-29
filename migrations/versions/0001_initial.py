"""Initial schema and database authorization."""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("""
    CREATE TABLE tenants (id uuid PRIMARY KEY, name text UNIQUE NOT NULL);
    CREATE TABLE users (
      id uuid PRIMARY KEY, tenant_id uuid NOT NULL REFERENCES tenants(id),
      email text UNIQUE NOT NULL, password_hash text NOT NULL,
      role text NOT NULL CHECK (role IN ('admin','manager','employee'))
    );
    CREATE TABLE documents (
      id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
      tenant_id uuid NOT NULL REFERENCES tenants(id), title text NOT NULL,
      source text NOT NULL, allowed_roles text[] NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now(),
      CHECK (array_length(allowed_roles, 1) > 0)
    );
    CREATE TABLE chunks (
      id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
      document_id bigint NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
      tenant_id uuid NOT NULL REFERENCES tenants(id),
      content text NOT NULL, embedding vector(128) NOT NULL,
      allowed_roles text[] NOT NULL, chunk_index integer NOT NULL,
      UNIQUE(document_id, chunk_index)
    );
    CREATE TABLE audit_logs (
      id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
      tenant_id uuid NOT NULL REFERENCES tenants(id), user_id uuid NOT NULL REFERENCES users(id),
      role text NOT NULL, query text NOT NULL, retrieved_chunk_ids bigint[] NOT NULL,
      answer_hash text, latency_ms integer NOT NULL, status text NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE INDEX chunks_tenant_roles_idx ON chunks (tenant_id);
    CREATE INDEX chunks_roles_gin_idx ON chunks USING gin (allowed_roles);
    CREATE INDEX chunks_embedding_hnsw_idx ON chunks USING hnsw (embedding vector_cosine_ops);
    CREATE INDEX audit_tenant_time_idx ON audit_logs (tenant_id, created_at DESC);
    ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
    ALTER TABLE documents FORCE ROW LEVEL SECURITY;
    ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
    ALTER TABLE chunks FORCE ROW LEVEL SECURITY;
    ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
    ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY;
    CREATE POLICY documents_scope ON documents USING (
      tenant_id::text = current_setting('app.tenant_id', true)
      AND current_setting('app.role', true) = ANY(allowed_roles)
    ) WITH CHECK (
      tenant_id::text = current_setting('app.tenant_id', true)
      AND current_setting('app.role', true) = ANY(allowed_roles)
    );
    CREATE POLICY chunks_scope ON chunks USING (
      tenant_id::text = current_setting('app.tenant_id', true)
      AND current_setting('app.role', true) = ANY(allowed_roles)
    ) WITH CHECK (
      tenant_id::text = current_setting('app.tenant_id', true)
      AND current_setting('app.role', true) = ANY(allowed_roles)
    );
    CREATE POLICY audit_scope ON audit_logs USING (
      tenant_id::text = current_setting('app.tenant_id', true)
      AND (current_setting('app.role', true) = 'admin' OR user_id::text = current_setting('app.user_id', true))
    ) WITH CHECK (
      tenant_id::text = current_setting('app.tenant_id', true)
      AND user_id::text = current_setting('app.user_id', true)
    );
    GRANT SELECT ON tenants, users TO rag_app;
    GRANT SELECT, INSERT ON documents, chunks, audit_logs TO rag_app;
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO rag_app;
    """)

def downgrade():
    op.execute("DROP TABLE audit_logs, chunks, documents, users, tenants CASCADE")
