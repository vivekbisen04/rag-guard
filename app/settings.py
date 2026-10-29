import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rag_app:dev-app-password@localhost:5432/postgres")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-change-this-secret-before-deploying")
JWT_ISSUER = "rag-guard"
JWT_AUDIENCE = "rag-guard-api"
ROLES = {"admin", "manager", "employee"}
