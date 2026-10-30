"""Create a user in an existing tenant with an interactive password prompt."""
import argparse
import getpass
import os
from uuid import uuid4

import psycopg

from app.auth import hash_password
from app.settings import ROLES


def create_user(database_url: str, tenant_name: str, email: str, role: str, password: str):
    with psycopg.connect(database_url) as conn:
        tenant = conn.execute("SELECT id FROM tenants WHERE name = %s", (tenant_name,)).fetchone()
        if tenant is None:
            raise ValueError(f"Unknown tenant: {tenant_name}")
        user_id = uuid4()
        conn.execute(
            "INSERT INTO users (id, tenant_id, email, password_hash, role) VALUES (%s, %s, %s, %s, %s)",
            (user_id, tenant[0], email, hash_password(password), role),
        )
    return user_id


def main():
    parser = argparse.ArgumentParser(description="Create an account in an existing tenant")
    parser.add_argument("--tenant", required=True, help="Existing tenant name, e.g. alpha")
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", choices=sorted(ROLES), default="employee")
    args = parser.parse_args()
    email = args.email.strip().lower()
    if not email or "@" not in email:
        parser.error("Enter a valid email address")
    password = getpass.getpass("New password: ")
    if len(password) < 12:
        parser.error("Password must have at least 12 characters")
    try:
        user_id = create_user(os.environ["ADMIN_DATABASE_URL"], args.tenant, email, args.role, password)
    except psycopg.errors.UniqueViolation:
        parser.error(f"Account already exists: {email}")
    except ValueError as error:
        parser.error(str(error))
    print(f"Created {args.role} account {email} in {args.tenant} (id: {user_id})")


if __name__ == "__main__":
    main()
