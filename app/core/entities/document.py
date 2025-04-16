# core/entities/document.py
from typing import Dict, List, Optional, Any
import uuid


class Document:
    """
    Entity class representing a document.

    This class represents a document in the system with its content, metadata,
    and embedding for similarity search.

    Attributes:
        id (str): Unique identifier for the document.
        content (str): Textual content of the document.
        metadata (Dict[str, Any]): Additional metadata about the document.
        embedding (List[float]): Vector embedding of the document.
        created_at (str): Timestamp of when the document was created.
        updated_at (str): Timestamp of when the document was last updated.
        source (str): Source of the document.
        user_id (str): ID of the user who owns the document.
    """

    def __init__(
            self,
            content: str,
            metadata: Dict[str, Any] = None,
            id: str = None,
            embedding: List[float] = None,
            created_at: str = None,
            updated_at: str = None,
            source: str = None,
            owner_id: str = None,
            file_id: str = None,
    ):
        """
        Initialize a new Document.

        Args:
            content (str): Textual content of the document.
            metadata (Dict[str, Any], optional): Additional metadata. Defaults to None.
            id (str, optional): Unique identifier. If None, a UUID is generated. Defaults to None.
            embedding (List[float], optional): Vector embedding. Defaults to None.
            created_at (str, optional): Creation timestamp. Defaults to None.
            updated_at (str, optional): Update timestamp. Defaults to None.
            source (str, optional): Source of the document. Defaults to None.
            owner_id (str, optional): User ID. Defaults to None.

        """
        self.id = id if id is not None else str(uuid.uuid4())
        self.content = content
        self.metadata = metadata or {}
        self.embedding = embedding
        self.created_at = created_at
        self.updated_at = updated_at
        self.source = source
        self.owner_id = owner_id
        self.file_id = file_id

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the document to a dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of the document.
        """
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "embedding": self.embedding,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source": self.source,
            'owner_id': self.owner_id,
            'file_id': self.file_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Document':
        """
        Create a new Document from a dictionary.

        Args:
            data (Dict[str, Any]): Dictionary representation of a document.

        Returns:
            Document: A new Document instance.
        """
        return cls(
            id=data.get("id"),
            content=data.get("content"),
            metadata=data.get("metadata"),
            embedding=data.get("embedding"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            source=data.get("source"),
        )

    def __repr__(self) -> str:
        """
        String representation of the document.

        Returns:
            str: String representation.
        """
        return f"Document(id={self.id}, content={self.content[:50]}...)"