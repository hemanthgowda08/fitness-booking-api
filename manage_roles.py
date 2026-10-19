"""Trusted local-only role administration for the FOR·MA API."""

import argparse

from sqlalchemy import select

import models
from database import Base, SessionLocal, engine
from migrations import migrate_database

# Running the trusted local command is also safe immediately after upgrading an
# older installation: it creates missing tables and applies additive migrations.
Base.metadata.create_all(bind=engine)
migrate_database(engine)


def set_role(email: str, role: str, confirmed: bool) -> int:
    """Set an existing user's role; this is idempotent and requires --confirm."""
    if not confirmed:
        print("Refusing to change a role without --confirm.")
        return 2
    normalized_email = email.strip().lower()
    if not normalized_email:
        print("Email is required.")
        return 2
    db = SessionLocal()
    try:
        user = db.scalar(select(models.User).where(models.User.email == normalized_email))
        if user is None:
            print(f"No user exists with email: {normalized_email}")
            return 1
        if user.role == role:
            print(f"{normalized_email} is already a {role}.")
            return 0
        user.role = role
        db.commit()
        print(f"Updated {normalized_email} to {role}.")
        return 0
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Trusted local role management for FOR·MA.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command, role in (("promote-admin", "admin"), ("promote-host", "host")):
        subparser = subparsers.add_parser(command, help=f"Promote an existing user to {role}.")
        subparser.add_argument("email", help="Existing account email")
        subparser.add_argument("--confirm", action="store_true", help="Confirm this local role change")
        subparser.set_defaults(role=role)
    args = parser.parse_args()
    return set_role(args.email, args.role, args.confirm)


if __name__ == "__main__":
    raise SystemExit(main())
