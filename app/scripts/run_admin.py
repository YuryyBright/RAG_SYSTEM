import argparse
import asyncio
import logging
from getpass import getpass
from typing import Optional

from sqlalchemy import inspect, text, select
from sqlalchemy.ext.asyncio import AsyncSession

from passlib.context import CryptContext

from app.infrastructure.database.db_models import User
from app.infrastructure.database.repository import AsyncSessionLocal
from app.utils.logger_util import get_logger

# Configure logger
logger = get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """
    Hash a plaintext password.

    Parameters
    ----------
    password : str
        The plaintext password to hash.

    Returns
    -------
    str
        The hashed password.
    """
    return pwd_context.hash(password)


async def add_user(db: AsyncSession, username: str, email: str, password: str, is_admin: bool = False) -> None:
    """
    Add a new user to the database.

    Parameters
    ----------
    db : AsyncSession
        The database session.
    username : str
        The username of the new user.
    email : str
        The email of the new user.
    password : str
        The plaintext password of the new user.
    is_admin : bool, optional
        Whether the new user should have admin privileges (default is False).
    """
    result = await db.execute(
        text("SELECT * FROM users WHERE username=:username OR email=:email"),
        {"username": username, "email": email}
    )
    existing = result.first()
    if existing:
        logger.warning("User with that username or email already exists.")
        return

    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        is_admin=is_admin
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info(f"User '{username}' created successfully.")


async def remove_user(db: AsyncSession, username: str) -> None:
    """
    Remove a user by their username.

    Parameters
    ----------
    db : AsyncSession
        The database session.
    username : str
        The username of the user to remove.
    """
    result = await db.execute(
        text("SELECT * FROM users WHERE username=:username"),
        {"username": username}
    )
    user = result.scalar_one_or_none()
    if not user:
        logger.warning("User not found.")
        return

    await db.delete(user)
    await db.commit()
    logger.info(f"User '{username}' deleted successfully.")


async def list_users(db: AsyncSession) -> None:
    """
    Log all users in the database.

    Parameters
    ----------
    db : AsyncSession
        The database session.
    """
    result = await db.execute(text("SELECT * FROM users"))
    users = result.fetchall()
    logger.info(f"Found {len(users)} users:")
    for row in users:
        role = "Admin" if row.is_admin else "User"
        logger.info(f" - {row.username} ({row.email}) [{role}]")


async def list_tables(db: AsyncSession) -> None:
    """
    Log all tables and their row counts.

    Parameters
    ----------
    db : AsyncSession
        The database session.
    """
    inspector = inspect(db.bind.sync_engine)
    tables = inspector.get_table_names()
    logger.info("Tables and row counts:")
    for table in tables:
        result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
        count = result.scalar()
        logger.info(f" - {table}: {count} rows")


async def find_user(db: AsyncSession, username: str) -> Optional[User]:
    """
    Find and log a specific user by username.

    Parameters
    ----------
    db : AsyncSession
        The database session.
    username : str
        The username of the user to find.

    Returns
    -------
    Optional[User]
        The found user, or None if not found.
    """
    result = await db.execute(
        text("SELECT * FROM users WHERE username=:username"),
        {"username": username}
    )
    user = result.first()
    if user:
        logger.info(f"User found: {user.username} ({user.email})")
    else:
        logger.warning("User not found.")
    return user


async def toggle_user_active(db: AsyncSession, username: str, active: bool) -> None:
    """
    Toggle the active status of a user.

    Parameters
    ----------
    db : AsyncSession
        The database session.
    username : str
        The username of the user to toggle.
    active : bool
        The new active status.
    """
    result = await db.execute(
        text("SELECT * FROM users WHERE username=:username"),
        {"username": username}
    )
    user = result.scalar_one_or_none()
    if not user:
        logger.warning("User not found.")
        return

    user.is_active = active
    await db.commit()
    logger.info(f"User '{username}' active status set to {active}.")


async def change_user_password(db: AsyncSession, username: str) -> None:
    """
    Change the password for a given user.

    Parameters
    ----------
    db : AsyncSession
        The database session.
    username : str
        The username of the user whose password is to be changed.
    """
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        logger.warning("User not found.")
        return

    new_password = getpass("New Password: ")
    confirm_password = getpass("Confirm New Password: ")
    if new_password != confirm_password:
        logger.warning("Passwords do not match.")
        return

    user.hashed_password = get_password_hash(new_password)
    await db.commit()
    logger.info(f"Password for user '{username}' has been updated.")


async def main_async(args):
    """
    Main asynchronous function to handle CLI commands.

    Parameters
    ----------
    args : argparse.Namespace
        The parsed command-line arguments.
    """
    async with AsyncSessionLocal() as db:
        if args.command == "add_user":
            password = getpass("Password: ")
            confirm = getpass("Confirm Password: ")
            if password != confirm:
                logger.warning("Passwords do not match.")
                return
            await add_user(db, args.username, args.email, password, args.admin)

        elif args.command == "remove_user":
            await remove_user(db, args.username)

        elif args.command == "list_users":
            await list_users(db)

        elif args.command == "list_tables":
            await list_tables(db)

        elif args.command == "find_user":
            await find_user(db, args.username)

        elif args.command == "toggle_active":
            await toggle_user_active(db, args.username, args.active)
        elif args.command == "change_password":
            await change_user_password(db, args.username)
        else:
            print("Unknown command")


def main():
    """
    Main function to parse command-line arguments and run the appropriate command.
    """
    parser = argparse.ArgumentParser(description="Admin CLI for managing users and DB.")
    subparsers = parser.add_subparsers(dest="command")

    add_user_cmd = subparsers.add_parser("add_user", help="Add a new user")
    add_user_cmd.add_argument("username", type=str)
    add_user_cmd.add_argument("email", type=str)
    add_user_cmd.add_argument("--admin", action="store_true", help="Grant admin privileges")
    change_pw_cmd = subparsers.add_parser("change_password", help="Change user password")
    change_pw_cmd.add_argument("username", type=str)
    rm_user_cmd = subparsers.add_parser("remove_user", help="Remove a user")
    rm_user_cmd.add_argument("username", type=str)

    subparsers.add_parser("list_users", help="List all users")
    subparsers.add_parser("list_tables", help="List all tables and row counts")

    find_user_cmd = subparsers.add_parser("find_user", help="Find a user by username")
    find_user_cmd.add_argument("username", type=str)

    toggle_active_cmd = subparsers.add_parser("toggle_active", help="Toggle user active status")
    toggle_active_cmd.add_argument("username", type=str)
    toggle_active_cmd.add_argument("--active", type=bool, required=True)

    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
