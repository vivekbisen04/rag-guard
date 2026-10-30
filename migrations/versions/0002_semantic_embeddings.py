"""Replace hash vectors with local semantic embeddings without losing chunks."""
import hashlib
import math
import re

from alembic import op
from sqlalchemy import text

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    # All work is in Alembic's transaction: a failed model load or backfill leaves
    # the old vectors and index intact. Chunk IDs and audit references are preserved.
    from app.embed import embed, get_model

    get_model()
    bind = op.get_bind()
    op.execute("ALTER TABLE chunks ADD COLUMN embedding_next vector(384)")
    rows = bind.execute(text("SELECT id, content FROM chunks ORDER BY id")).fetchall()
    for row in rows:
        bind.execute(
            text("UPDATE chunks SET embedding_next = CAST(:embedding AS vector) WHERE id = :id"),
            {"embedding": embed(row.content), "id": row.id},
        )
    op.execute("DROP INDEX chunks_embedding_hnsw_idx")
    op.execute("ALTER TABLE chunks DROP COLUMN embedding")
    op.execute("ALTER TABLE chunks RENAME COLUMN embedding_next TO embedding")
    op.execute("ALTER TABLE chunks ALTER COLUMN embedding SET NOT NULL")
    op.execute("CREATE INDEX chunks_embedding_hnsw_idx ON chunks USING hnsw (embedding vector_cosine_ops)")


def _legacy_embed(content):
    values = [0.0] * 128
    for token in re.findall(r"[a-z0-9]+", content.lower()):
        digest = hashlib.sha256(token.encode()).digest()
        index = int.from_bytes(digest[:4], "big") % 128
        values[index] += 1 if digest[4] & 1 else -1
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return "[" + ",".join(f"{value / norm:.8f}" for value in values) + "]"


def downgrade():
    bind = op.get_bind()
    op.execute("ALTER TABLE chunks ADD COLUMN embedding_old vector(128)")
    rows = bind.execute(text("SELECT id, content FROM chunks ORDER BY id")).fetchall()
    for row in rows:
        bind.execute(
            text("UPDATE chunks SET embedding_old = CAST(:embedding AS vector) WHERE id = :id"),
            {"embedding": _legacy_embed(row.content), "id": row.id},
        )
    op.execute("DROP INDEX chunks_embedding_hnsw_idx")
    op.execute("ALTER TABLE chunks DROP COLUMN embedding")
    op.execute("ALTER TABLE chunks RENAME COLUMN embedding_old TO embedding")
    op.execute("ALTER TABLE chunks ALTER COLUMN embedding SET NOT NULL")
    op.execute("CREATE INDEX chunks_embedding_hnsw_idx ON chunks USING hnsw (embedding vector_cosine_ops)")
