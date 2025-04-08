# core/entities/user.py
from typing import Dict, Any, List, Optional
import uuid


class User:
    """
    Entity class representing a user.

    This class represents a user in the system with authentication details
    and associated metadata.

    Attributes:
        id (str): Unique identifier for the user.
        username (str): Username for login.
        email (str): Email address of the user.
        hashed_password (str): Hashed password for authentication.
        is_active (bool): Flag indicating if the user account is active.
        is_admin (bool): Flag indicating if the user has admin privileges.
        created_at (str): Timestamp of when the user was created.
        updated_at (str): Timestamp of when the user was last updated.
        metadata (Dict[str, Any]): Additional metadata about the user.
    """

    def __init__(
            self,
            username: str,
            email: str,
            hashed_password: str,
            id: str = None,
            is_active: bool = True,
            is_admin: bool = False,
            created_at: str = None,
            updated_at: str = None,
            metadata: Dict[str, Any] = None
    ):
        """
        Initialize a new User.

        Args:
            username (str): Username for login.
            email (str): Email address of the user.
            hashed_password (str): Hashed password for authentication.
            id (str, optional): Unique identifier. If None, a UUID is generated. Defaults to None.
            is_active (bool, optional): Account active status. Defaults to True.
            is_admin (bool, optional): Admin status. Defaults to False.
            created_at (str, optional): Creation timestamp. Defaults to None.
            updated_at (str, optional): Update timestamp. Defaults to None.
            metadata (Dict[str, Any], optional): Additional metadata. Defaults to None.
        """
        self.id = id if id is not None else str(uuid.uuid4())
        self.username = username
        self.email = email
        self.hashed_password = hashed_password
        self.is_active = is_active
        self.is_admin = is_admin
        self.created_at = created_at
        self.updated_at = updated_at
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the user to a dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of the user.
        """
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "hashed_password": self.hashed_password,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """
        Create a new User from a dictionary.

        Args:
            data (Dict[str, Any]): Dictionary representation of a user.

        Returns:
            User: A new User instance.
        """
        return cls(
            id=data.get("id"),
            username=data.get("username"),
            email=data.get("email"),
            hashed_password=data.get("hashed_password"),
            is_active=data.get("is_active", True),
            is_admin=data.get("is_admin", False),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            metadata=data.get("metadata")
        )

    def __repr__(self) -> str:
        """
        String representation of the user.

        Returns:
            str: String representation.
        """
        return f"User(id={self.id}, username={self.username}, email={self.email})"