from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ----- Pydantic Models -----

class ProfileUpdate(BaseModel):
    """
    Model for updating user profile information.

    Attributes
    ----------
    name : str
        The name of the user.
    email : str
        The email address of the user.
    timezone : str
        The timezone of the user.
    theme : str
        The preferred theme of the user (e.g., light or dark mode).
    """
    name: str
    email: str
    timezone: str
    theme: str


class PasswordChange(BaseModel):
    """
    Model for changing a user's password.

    Attributes
    ----------
    current_password : str
        The user's current password.
    new_password : str
        The new password the user wants to set.
    """
    current_password: str
    new_password: str


class ApiKeyResponse(BaseModel):
    """
    Model for API key response data.

    Attributes
    ----------
    id : int
        The unique identifier of the API key.
    name : str
        The name of the API key.
    key : Optional[str]
        The actual API key value (optional, may not always be returned).
    created_at : datetime
        The timestamp when the API key was created.
    last_used : Optional[datetime]
        The timestamp of the last usage of the API key (optional).
    """
    id: int
    name: str
    key: Optional[str] = None
    created_at: datetime
    last_used: Optional[datetime] = None


class ApiKeyCreate(BaseModel):
    """
    Model for creating a new API key.

    Attributes
    ----------
    name : str
        The name of the API key to be created.
    """
    name: str


class UserActivityResponse(BaseModel):
    """
    Model for user activity response data.

    Attributes
    ----------
    id : int
        The unique identifier of the activity.
    type : str
        The type of activity (e.g., login, query, etc.).
    description : str
        A description of the activity.
    timestamp : datetime
        The timestamp when the activity occurred.
    """
    id: int
    type: str
    description: str
    timestamp: datetime


class UserStats(BaseModel):
    """
    Model for user statistics.

    Attributes
    ----------
    query_stats : dict
        A dictionary containing statistics related to user queries.
    doc_stats : dict
        A dictionary containing statistics related to user documents.
    """
    query_stats: dict
    doc_stats: dict
