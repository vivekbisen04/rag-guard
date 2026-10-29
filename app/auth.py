import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from .db import connection
from .settings import JWT_SECRET, JWT_ISSUER, JWT_AUDIENCE, ROLES

bearer = HTTPBearer(auto_error=False)

def hash_password(password, salt=None):
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"{salt.hex()}:{digest.hex()}"

def verify_password(password, stored):
    try:
        salt, expected = stored.split(":", 1)
        actual = hash_password(password, bytes.fromhex(salt)).split(":", 1)[1]
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False

def login(email, password):
    with connection() as conn:
        user = conn.execute("SELECT id, tenant_id, email, role, password_hash FROM users WHERE email = %s", (email,)).fetchone()
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user["id"]), "tenant_id": str(user["tenant_id"]),
               "role": user["role"], "iss": JWT_ISSUER, "aud": JWT_AUDIENCE,
               "iat": now, "exp": now + timedelta(hours=1)}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def identity(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if credentials is None:
        raise HTTPException(401, "Bearer token required")
    try:
        claims = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"],
                            issuer=JWT_ISSUER, audience=JWT_AUDIENCE,
                            options={"require": ["sub", "tenant_id", "role", "exp", "iat", "iss", "aud"]})
        user_id = UUID(claims["sub"])
        tenant_id = UUID(claims["tenant_id"])
        role = claims["role"]
        if role not in ROLES:
            raise ValueError("Invalid role")
    except (jwt.InvalidTokenError, ValueError, KeyError, TypeError):
        raise HTTPException(401, "Invalid token") from None
    with connection() as conn:
        user = conn.execute("SELECT tenant_id, role FROM users WHERE id = %s", (user_id,)).fetchone()
    if not user or user["tenant_id"] != tenant_id or user["role"] != role:
        raise HTTPException(401, "Invalid token identity")
    return {"user_id": user_id, "tenant_id": tenant_id, "role": role}
