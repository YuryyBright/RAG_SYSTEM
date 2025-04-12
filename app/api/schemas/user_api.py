from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


# -------------------------------
# User Profile and Authentication
# -------------------------------

class ProfileUpdate(BaseModel):
    """
    Schema for updating user profile information.

    Attributes
    ----------
    name : str
        Full name of the user.
    email : str
        Email address of the user.
    timezone : str
        User's timezone (e.g., "UTC", "Europe/Berlin").
    theme : str
        UI theme preference, such as "light" or "dark".
    """
    name: str
    email: str
    timezone: str
    theme: str


class PasswordChange(BaseModel):
    """
    Schema for changing a user's password.

    Attributes
    ----------
    current_password : str
        The user's current password.
    new_password : str
        The new password to set.
    """
    current_password: str
    new_password: str


# ----------------------
# API Key Management
# ----------------------

class ApiKeyCreate(BaseModel):
    """
    Schema for creating a new API key.

    Attributes
    ----------
    name : str
        Name or label for the API key.
    expires_days : Optional[int]
        Number of days before the key expires (None = no expiration).
    """
    name: str
    expires_days: Optional[int] = None


class ApiKeyResponse(BaseModel):
    """
    Schema for returning API key information to the client.

    Attributes
    ----------
    id : int
        Unique identifier for the API key.
    name : str
        Name or label for the key.
    key : Optional[str]
        The plain API key value (only shown once on creation).
    created_at : datetime
        Timestamp when the key was created.
    expires_at : Optional[datetime]
        Expiration time for the key (if applicable).
    last_used : Optional[datetime]
        Last time this key was used.
    """
    id: int
    name: str
    key: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None


# --------------------
# User Session Tracking
# --------------------


class SessionInfo(BaseModel):
    """
    Schema for representing an active user session.

    Attributes:
        id (str): Session ID token.
        device (Optional[str]): Device identifier (e.g., "iPhone 14", "Windows PC").
        browser (Optional[str]): Parsed browser name and version (e.g., "Chrome 122.0").
        os (Optional[str]): Operating system name and version (e.g., "Windows 11").
        ip_address (Optional[str]): IP address associated with the session.
        location (Optional[str]): Geographic location based on IP (e.g., "Berlin, Germany").
        created_at (datetime): Timestamp when the session was started.
        last_activity (Optional[datetime]): Last recorded activity timestamp.
        is_current (bool): Whether this session is the currently active one.
    """

    id: str = Field(..., description="Session ID token.")
    device: Optional[str] = Field(None, description='Device identifier (e.g., "iPhone 14", "Windows PC").')
    browser: Optional[str] = Field(None, description='Parsed browser name and version (e.g., "Chrome 122.0").')
    os: Optional[str] = Field(None, description='Operating system name and version (e.g., "Windows 11").')
    ip_address: Optional[str] = Field(None, description="IP address associated with the session.")
    location: Optional[str] = Field(None, description='Geographic location based on IP (e.g., "Berlin, Germany").')
    created_at: datetime = Field(..., description="Timestamp when the session was started.")
    last_activity: Optional[datetime] = Field(None, description="Last recorded activity timestamp.")
    is_current: bool = Field(..., description="Whether this session is the currently active one.")

    class Config:
        schema_extra = {
            "example": {
                "id": "cbe73d70-4f01-4b9a-83dc-6788bfc8d231",
                "device": "Windows PC",
                "browser": "Chrome 122.0",
                "os": "Windows 11",
                "ip_address": "192.168.1.100",
                "location": "Berlin, Germany",
                "created_at": "2025-04-10T12:34:56.789Z",
                "last_activity": "2025-04-10T14:01:22.456Z",
                "is_current": True
            }
        }




# -------------------------
# User Activity & Statistics
# -------------------------

class UserActivityResponse(BaseModel):
    """
    Schema for representing an individual user activity log entry.

    Attributes
    ----------
    id : int
        Activity log ID.
    type : str
        Type of activity (e.g., "login", "upload", "query").
    description : str
        Human-readable description of the activity.
    timestamp : datetime
        Timestamp when the activity occurred.
    """
    id: int
    type: str
    description: str
    timestamp: datetime

class UserStats(BaseModel):
    """
    Schema for summarizing a user's usage statistics.

    Attributes
    ----------
    query_stats : Dict[str, int]
        Dictionary of query activity counts grouped by date (YYYY-MM-DD) and count.
    doc_stats : Dict[str, List[str | int]]
        Document usage statistics: format {"labels": [doc_types], "data": [counts]}.
    file_count : int
        Total number of files uploaded by the user.
    login_count : int
        Total number of login actions by the user.
    query_count : int
        Total number of queries made by the user.
    upload_count : int
        Total number of file upload actions (may differ from file_count).
    """

    query_stats: Dict[str, int] = Field(..., example={"2024-04-01": 5, "2024-04-02": 3})
    doc_stats: Dict[str, List] = Field(
        ..., example={"labels": ["PDF", "Word", "Text", "Other"], "data": [10, 5, 15, 2]}
    )
    file_count: int = Field(..., example=25)
    login_count: int = Field(..., example=10)
    query_count: int = Field(..., example=20)
    upload_count: int = Field(..., example=8)



# ----------------------
# Notification Preferences
# ----------------------

class NotificationSettings(BaseModel):
    """
    Schema for user notification preferences.

    Attributes
    ----------
    email_notifications : bool
        Enable or disable email notifications.
    browser_notifications : bool
        Enable or disable browser push notifications.
    login_alerts : bool
        Enable alerts for new login activities.
    api_usage_alerts : bool
        Enable alerts when API keys are used.
    file_activity_notifications : bool
        Enable alerts when files are uploaded or accessed.
    """
    email_notifications: bool
    browser_notifications: bool
    login_alerts: bool
    api_usage_alerts: bool
    file_activity_notifications: bool


# --------------------
# Account Management
# --------------------

class AccountAction(BaseModel):
    """
    Schema for user account actions such as deactivation or reactivation.

    Attributes
    ----------
    action : str
        The action to perform. Expected values: "deactivate", "reactivate".
    """
    action: str


# --------------------
# Export Job Tracking
# --------------------

class ExportUserData(BaseModel):
    """
    Schema for representing a user data export job status.

    Attributes
    ----------
    job_id : str
        Unique identifier for the export job.
    status : str
        Current status of the job (e.g., "pending", "completed").
    created_at : datetime
        Timestamp when the job was scheduled.
    progress : int
        Export job progress in percentage (0-100).
    """
    job_id: str
    status: str
    created_at: datetime
    progress: int
