# core/entities/query.py
from typing import Dict, List, Any, Optional
import uuid


class Query:
    """
    Entity class representing a user query.

    This class represents a query in the system with its text,
    processed information, and associated metadata.

    Attributes:
        id (str): Unique identifier for the query.
        text (str): The query text.
        embedding (List[float]): Vector embedding of the query.
        metadata (Dict[str, Any]): Additional metadata about the query.
        user_id (str): ID of the user who made the query.
        created_at (str): Timestamp of when the query was created.
    """

    def __init__(
            self,
            text: str,
            embedding: List[float] = None,
            metadata: Dict[str, Any] = None,
            user_id: str = None,
            id: str = None,
            created_at: str = None
    ):
        """
        Initialize a new Query.

        Args:
            text (str): The query text.
            embedding (List[float], optional): Vector embedding. Defaults to None.
            metadata (Dict[str, Any], optional): Additional metadata. Defaults to None.
            user_id (str, optional): User ID. Defaults to None.
            id (str, optional): Unique identifier. If None, a UUID is generated. Defaults to None.
            created_at (str, optional): Creation timestamp. Defaults to None.
        """
        self.id = id if id is not None else str(uuid.uuid4())
        self.text = text
        self.embedding = embedding
        self.metadata = metadata or {}
        self.user_id = user_id
        self.created_at = created_at

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the query to a dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of the query.
        """
        return {
            "id": self.id,
            "text": self.text,
            "embedding": self.embedding,
            "metadata": self.metadata,
            "user_id": self.user_id,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Query':
        """
        Create a new Query from a dictionary.

        Args:
            data (Dict[str, Any]): Dictionary representation of a query.

        Returns:
            Query: A new Query instance.
        """
        return cls(
            id=data.get("id"),
            text=data.get("text"),
            embedding=data.get("embedding"),
            metadata=data.get("metadata"),
            user_id=data.get("user_id"),
            created_at=data.get("created_at")
        )

    def __repr__(self) -> str:
        """
        String representation of the query.

        Returns:
            str: String representation.
        """
        return f"Query(id={self.id}, text={self.text[:50]}...)"