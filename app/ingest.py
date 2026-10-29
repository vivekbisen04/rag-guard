from io import BytesIO
from pypdf import PdfReader
from fastapi import HTTPException
from .embed import embed

def extract_text(filename: str, data: bytes) -> str:
    if len(data) > 10_000_000:
        raise HTTPException(413, "File too large")
    suffix = filename.lower().rsplit(".", 1)[-1]
    try:
        if suffix == "pdf":
            text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(data)).pages)
        elif suffix in {"txt", "md", "markdown"}:
            text = data.decode("utf-8")
        else:
            raise HTTPException(415, "Supported formats: txt, md, pdf")
    except (UnicodeError, ValueError) as exc:
        raise HTTPException(400, "Could not read file") from exc
    if not text.strip():
        raise HTTPException(400, "No extractable text")
    return text

def chunks(text: str, size=650, overlap=100):
    words = text.split()
    for start in range(0, len(words), size - overlap):
        part = words[start:start + size]
        if part:
            yield " ".join(part)
        if start + size >= len(words):
            break

def store_document(conn, identity, title, source, text, allowed_roles):
    row = conn.execute("""INSERT INTO documents (tenant_id, title, source, allowed_roles)
        VALUES (%s,%s,%s,%s) RETURNING id""",
        (identity["tenant_id"], title, source, allowed_roles)).fetchone()
    for index, content in enumerate(chunks(text)):
        conn.execute("""INSERT INTO chunks
            (document_id, tenant_id, content, embedding, allowed_roles, chunk_index)
            VALUES (%s,%s,%s,%s::vector,%s,%s)""",
            (row["id"], identity["tenant_id"], content, embed(content), allowed_roles, index))
    return row["id"]
