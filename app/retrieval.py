from time import perf_counter
from .embed import embed

def retrieve(conn, query: str, tenant_id, role: str, limit: int = 5):
    if not tenant_id or not role:
        raise ValueError("tenant_id and role are required")
    start = perf_counter()
    query_vector = embed(query)
    conn.execute("SET LOCAL hnsw.iterative_scan = strict_order")
    rows = conn.execute("""SELECT c.id, c.document_id, d.title, c.content,
               c.embedding <=> %s::vector AS distance
        FROM chunks c JOIN documents d ON d.id = c.document_id
        WHERE c.tenant_id = %s AND %s = ANY(c.allowed_roles)
          AND d.tenant_id = %s AND %s = ANY(d.allowed_roles)
        ORDER BY c.embedding <=> %s::vector LIMIT %s""",
        (query_vector, tenant_id, role, tenant_id, role, query_vector, limit)).fetchall()
    return rows, round((perf_counter() - start) * 1000)
