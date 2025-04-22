"""
Utility functions for validation in the RAG system including input validation,
schema validation, and format verification.
"""
import re
import uuid
import json
from typing import Any, Dict, List, Optional, Union
import logging

from domain.interfaces.embedding import EmbeddingInterface

logger = logging.getLogger(__name__)

# Email validation regex pattern
EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# URL validation regex pattern
URL_PATTERN = r'^(https?:\/\/)?(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'

# UUID validation regex pattern
UUID_PATTERN = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'


def is_valid_email(email: str) -> bool:
    """
    Validate an email address format.

    Args:
        email: Email address to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not isinstance(email, str):
        return False
    return bool(re.match(EMAIL_PATTERN, email))


def is_valid_url(url: str) -> bool:
    """
    Validate a URL format.

    Args:
        url: URL to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not isinstance(url, str):
        return False
    return bool(re.match(URL_PATTERN, url))


def is_valid_uuid(uuid_str: str) -> bool:
    """
    Validate a UUID string format.

    Args:
        uuid_str: UUID string to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not isinstance(uuid_str, str):
        return False

    # Try with regex first (faster)
    if not re.match(UUID_PATTERN, uuid_str.lower()):
        return False

    # Additional validation by trying to parse it
    try:
        uuid_obj = uuid.UUID(uuid_str)
        return str(uuid_obj) == uuid_str.lower()
    except ValueError:
        return False


def is_valid_json(json_str: str) -> bool:
    """
    Validate whether a string is a valid JSON.

    Args:
        json_str: JSON string to validate

    Returns:
        bool: True if valid JSON, False otherwise
    """
    if not isinstance(json_str, str):
        return False
    try:
        json.loads(json_str)
        return True
    except (ValueError, TypeError):
        return False

def safe_parse_json(json_str: str) -> Optional[Union[Dict[str, Any], List[Any]]]:
    """
    Safely parse a JSON string and return a Python object.

    Args:
        json_str: JSON string

    Returns:
        Parsed Python object or None if invalid
    """
    if not is_valid_json(json_str):
        return None
    return json.loads(json_str)


# В utils/embedding_util.py або прямо в embedding_service.py
async def validate_embedding_dimensions(embedding_service: EmbeddingInterface, expected_dim: int = 1536):
    """Validates that the embedding model outputs vectors with the expected dimension."""
    try:
        dummy_text = "test validation text"
        embedding = await embedding_service.get_embedding(dummy_text)
        if len(embedding) != expected_dim:
            raise ValueError(
                f"Embedding dimension mismatch: got {len(embedding)}, expected {expected_dim}.\n"
                f"⚠️ Check the model or settings."
            )
    except Exception as e:
        raise RuntimeError(f"Failed to validate embedding dimensions: {str(e)}")
