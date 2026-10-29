import hashlib
import logging
import re
from pathlib import Path
from datetime import datetime
from time import perf_counter
from typing import Literal
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .auth import identity, login
from .db import connection
from .ingest import extract_text, store_document
from .llm import ProviderError, answer
from .retrieval import retrieve
from .settings import ROLES

app = FastAPI(title="RAG Guard")
logger = logging.getLogger(__name__)
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

class LoginRequest(BaseModel):
    email: str
    password: str

class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)

@app.get("/")
def index():
    return FileResponse(FRONTEND_DIST / "index.html")

@app.get("/health")
def health():
    with connection() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok"}

@app.post("/login")
def login_route(body: LoginRequest):
    return {"access_token": login(body.email, body.password), "token_type": "bearer"}

@app.get("/me")
def me(user=Depends(identity)):
    return {"user_id": user["user_id"], "tenant_id": user["tenant_id"], "role": user["role"]}

@app.post("/ingest")
async def ingest_route(title: str = Form(...), allowed_roles: str = Form(...),
                       file: UploadFile = File(...), user=Depends(identity)):
    if user["role"] != "admin":
        raise HTTPException(403, "Admin role required")
    roles = sorted(set(r.strip() for r in allowed_roles.split(",")))
    if not roles or not set(roles) <= ROLES or "admin" not in roles:
        raise HTTPException(400, "Use comma-separated roles including admin")
    filename = file.filename or "upload.txt"
    text = extract_text(filename, await file.read(10_000_001))
    with connection(user) as conn:
        document_id = store_document(conn, user, title, filename, text, roles)
    return {"document_id": document_id}

@app.post("/chat")
def chat_route(body: ChatRequest, user=Depends(identity)):
    start = perf_counter()
    rows = []
    retrieval_ms = 0
    status = "ok"
    result = None
    error = None
    try:
        with connection(user) as conn:
            rows, retrieval_ms = retrieve(conn, body.query, user["tenant_id"], user["role"])
        result = answer(body.query, rows)
        if not rows:
            status = "empty"
        # Do not present model-invented chunk IDs as citations.
        ids = {r["id"] for r in rows}
        result = re.sub(r"\[chunk (\d+)\]", lambda m: m.group(0) if int(m.group(1)) in ids else "", result)
    except ProviderError as exc:
        status = "error"
        error = exc
        logger.warning("Answer provider failed: provider=%s status=%s", exc.provider, exc.status_code)
    except Exception as exc:
        status = "error"
        error = exc
        logger.exception("Chat request failed")
    elapsed = round((perf_counter() - start) * 1000)
    with connection(user) as conn:
        conn.execute("""INSERT INTO audit_logs
          (tenant_id,user_id,role,query,retrieved_chunk_ids,answer_hash,latency_ms,status)
          VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
          (user["tenant_id"], user["user_id"], user["role"], body.query,
           [r["id"] for r in rows], hashlib.sha256(result.encode()).hexdigest() if result else None,
           elapsed, status))
    if error:
        detail = str(error) if isinstance(error, ProviderError) else "Chat request failed; see API logs"
        raise HTTPException(503, detail) from error
    return {"answer": result, "sources": [{"chunk_id": r["id"], "document_id": r["document_id"],
            "title": r["title"]} for r in rows], "retrieval_ms": retrieval_ms}

@app.get("/admin/audit")
def audit_route(user_id: str | None = None, since: datetime | None = None,
                until: datetime | None = None, limit: int = Query(100, ge=1, le=500),
                user=Depends(identity)):
    if user["role"] != "admin":
        raise HTTPException(403, "Admin role required")
    with connection(user) as conn:
        rows = conn.execute("""SELECT id,tenant_id,user_id,role,query,retrieved_chunk_ids,
                  answer_hash,latency_ms,status,created_at FROM audit_logs
                  WHERE tenant_id = %s AND (%s::uuid IS NULL OR user_id = %s::uuid)
                    AND (%s::timestamptz IS NULL OR created_at >= %s::timestamptz)
                    AND (%s::timestamptz IS NULL OR created_at <= %s::timestamptz)
                  ORDER BY created_at DESC LIMIT %s""",
                  (user["tenant_id"], user_id, user_id, since, since, until, until, limit)).fetchall()
    return rows
