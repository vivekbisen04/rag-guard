"""Idempotent demo data with three tenants and all three roles."""
import os
from uuid import uuid5, NAMESPACE_DNS
import psycopg
from app.auth import hash_password
from app.embed import embed

URL = os.environ["ADMIN_DATABASE_URL"]
PASSWORD = os.getenv("SEED_PASSWORD", "demo-password")

def uid(name):
    return uuid5(NAMESPACE_DNS, "rag-guard/" + name)

def main():
    with psycopg.connect(URL) as conn:
        for tenant in ("alpha", "beta", "gamma"):
            tid = uid(tenant)
            conn.execute("INSERT INTO tenants(id,name) VALUES (%s,%s) ON CONFLICT DO NOTHING", (tid, tenant))
            for role in ("admin", "manager", "employee"):
                email = f"{role}@{tenant}.example"
                conn.execute("""INSERT INTO users(id,tenant_id,email,password_hash,role)
                    VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                    (uid(email), tid, email, hash_password(PASSWORD), role))
            for index in range(20):
                level = index % 3
                roles = (["admin", "manager", "employee"], ["admin", "manager"], ["admin"])[level]
                marker = f"CANARY_{tenant.upper()}_{index:02d}_ACCESS"
                title = f"{tenant.capitalize()} policy {index:02d}"
                content = f"{title}. Access level {roles[-1]}. Unique reference {marker}. This document belongs to {tenant}."
                existing = conn.execute("SELECT id FROM documents WHERE tenant_id=%s AND title=%s", (tid, title)).fetchone()
                if existing:
                    continue
                doc = conn.execute("INSERT INTO documents(tenant_id,title,source,allowed_roles) VALUES (%s,%s,%s,%s) RETURNING id",
                                   (tid, title, "seed", roles)).fetchone()[0]
                conn.execute("""INSERT INTO chunks(document_id,tenant_id,content,embedding,allowed_roles,chunk_index)
                    VALUES (%s,%s,%s,%s::vector,%s,0)""", (doc, tid, content, embed(content), roles))
    print("Seeded 3 tenants, 9 users, 60 documents")

if __name__ == "__main__":
    main()
