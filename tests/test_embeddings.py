import math

from app.embed import DIMENSIONS, embed


def test_semantic_embedding_matches_database_dimension():
    vector = [float(value) for value in embed("software engineer and developer tools")[1:-1].split(",")]
    assert len(vector) == DIMENSIONS == 384
    assert math.isclose(math.sqrt(sum(value * value for value in vector)), 1.0, abs_tol=1e-5)


def test_existing_chunks_have_semantic_vectors():
    from app.db import connection

    with connection() as conn:
        # RLS hides chunks without identity, so use an authorized demo identity.
        user = conn.execute("SELECT id, tenant_id, role FROM users WHERE email=%s", ("admin@alpha.example",)).fetchone()
    identity = {"user_id": user["id"], "tenant_id": user["tenant_id"], "role": user["role"]}
    with connection(identity) as conn:
        row = conn.execute(
            "SELECT count(*) AS total, count(*) FILTER (WHERE vector_dims(embedding) <> 384) AS mismatched FROM chunks"
        ).fetchone()
    assert row["total"] > 0
    assert row["mismatched"] == 0
