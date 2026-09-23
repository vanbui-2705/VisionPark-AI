"""CLI for creating VisionPark users with an assigned application role."""

import argparse
import getpass
import os
import re
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.database.session import database
from app.modules.users.models import Role, User
from app.modules.users.schemas import RoleName

USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
MIN_PASSWORD_LENGTH = 8


def create_user(
    session: Session,
    *,
    username: str,
    display_name: str,
    password: str,
    role_name: RoleName,
) -> User:
    """Add one active user to a session, rejecting invalid or duplicate input."""

    normalized_username = username.strip().lower()
    normalized_display_name = display_name.strip()
    if not normalized_username or len(normalized_username) > 64:
        raise ValueError("Username must contain between 1 and 64 characters.")
    if not USERNAME_PATTERN.fullmatch(normalized_username):
        raise ValueError(
            "Username may contain only lowercase letters, numbers, dots, underscores, and hyphens."
        )
    if not normalized_display_name or len(normalized_display_name) > 120:
        raise ValueError("Display name must contain between 1 and 120 characters.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must contain at least {MIN_PASSWORD_LENGTH} characters.")
    if session.scalar(select(User).where(User.username == normalized_username)) is not None:
        raise ValueError(f"Username '{normalized_username}' already exists.")

    role = session.scalar(select(Role).where(Role.name == role_name.value))
    if role is None:
        role = Role(name=role_name.value)
        session.add(role)
        session.flush()

    user = User(
        username=normalized_username,
        display_name=normalized_display_name,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
    session.add(user)
    session.flush()
    return user


def _parse_role(value: str) -> RoleName:
    try:
        return RoleName(value.strip().upper())
    except ValueError as exc:
        choices = ", ".join(role.value for role in RoleName)
        raise argparse.ArgumentTypeError(f"role must be one of: {choices}") from exc


def _read_password(password_env: str | None = None) -> str:
    if password_env:
        password = os.getenv(password_env)
        if password is None:
            raise ValueError(f"Environment variable '{password_env}' is not set.")
        return password

    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise ValueError("Password confirmation does not match.")
    return password


def _create_and_commit(
    session: Session,
    *,
    username: str,
    display_name: str,
    password: str,
    role_name: RoleName,
) -> User:
    try:
        user = create_user(
            session,
            username=username,
            display_name=display_name,
            password=password,
            role_name=role_name,
        )
        session.commit()
        return user
    except (IntegrityError, ValueError):
        session.rollback()
        raise


def _run_interactive(session: Session) -> int:
    roles = ", ".join(role.value for role in RoleName)
    print("Create VisionPark users. Leave username blank to finish.")
    print(f"Available roles: {roles}")
    created_count = 0

    while True:
        username = input("\nUsername: ").strip()
        if not username:
            break
        display_name = input("Display name: ").strip()
        try:
            role_name = _parse_role(input("Role: "))
            password = _read_password()
            user = _create_and_commit(
                session,
                username=username,
                display_name=display_name,
                password=password,
                role_name=role_name,
            )
        except (ValueError, IntegrityError) as exc:
            print(f"Error: {exc}")
            continue

        created_count += 1
        print(f"Created '{user.username}' with role {user.role.name}.")

    print(f"Finished. Created {created_count} user(s).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create an active VisionPark account and assign an application role."
    )
    parser.add_argument("--username", help="Unique username (stored in lowercase).")
    parser.add_argument("--display-name", help="Name displayed in the application.")
    parser.add_argument(
        "--role",
        type=_parse_role,
        help="ADMIN, OPERATOR, ACCOUNTANT, or TECHNICIAN.",
    )
    parser.add_argument(
        "--password-env",
        metavar="VARIABLE",
        help="Read the password from this environment variable instead of prompting.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command_values = (args.username, args.display_name, args.role)
    command_mode = any(value is not None for value in command_values)
    if command_mode and not all(value is not None for value in command_values):
        parser.error("--username, --display-name, and --role must be provided together")
    if args.password_env and not command_mode:
        parser.error("--password-env requires --username, --display-name, and --role")

    settings = get_settings()
    database.configure(settings.database_url, echo=settings.database_echo)
    try:
        with database.create_session() as session:
            if not command_mode:
                return _run_interactive(session)

            try:
                password = _read_password(args.password_env)
                user = _create_and_commit(
                    session,
                    username=args.username,
                    display_name=args.display_name,
                    password=password,
                    role_name=args.role,
                )
            except (ValueError, IntegrityError) as exc:
                parser.exit(1, f"Error: {exc}\n")
            print(f"Created '{user.username}' with role {user.role.name}.")
            return 0
    finally:
        database.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
