
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from typing import List


class UserInfo(BaseModel):
    """Schema for user information returned from authentication endpoints."""
    id: str
    username: str
    email: EmailStr
    display_name: Optional[str] = None
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    is_active: bool = True
    is_verified: bool = False
    avatar_url: Optional[str] = None

    class Config:
        orm_mode = True
class ActivityLogEntry(BaseModel):
    """
    Schema for user activity log entry.

    Attributes
    ----------
    user_id : str
        The ID of the user who performed the activity.
    action : str
        The action performed by the user.
    timestamp : datetime
        The timestamp when the activity occurred.
    details : Optional[str]
        Additional details about the activity.
    """
    user_id: str = Field(..., description="User ID")
    action: str = Field(..., description="Action performed by the user")
    timestamp: datetime = Field(..., description="Timestamp of the activity")
    details: Optional[str] = Field(None, description="Additional details about the activity")



class ActivityLogResponse(BaseModel):
    """
    Schema for user activity log response.

    Attributes
    ----------
    activities : List[ActivityLogEntry]
        A list of activity log entries.
    """
    activities: List[ActivityLogEntry] = Field(default_factory=list, description="List of activity log entries")


class NotificationEntry(BaseModel):
    """
    Schema for user notification entry.

    Attributes
    ----------
    user_id : str
        The ID of the user receiving the notification.
    message : str
        The notification message.
    timestamp : datetime
        The timestamp when the notification was created.
    read : bool
        Indicates whether the notification has been read.
    """
    user_id: str = Field(..., description="User ID")
    message: str = Field(..., description="Notification message")
    timestamp: datetime = Field(..., description="Timestamp of the notification")
    read: bool = Field(False, description="Read status of the notification")

class NotificationResponse(BaseModel):
    """
    Schema for user notification response.

    Attributes
    ----------
    notifications : List[NotificationEntry]
        A list of notification entries.
    """
    notifications: List[NotificationEntry] = Field(default_factory=list, description="List of notification entries")


class Permission(BaseModel):
    """
    Schema for permission.

    Attributes
    ----------
    name : str
        The name of the permission.
    description : str
        A brief description of what the permission allows.
    """
    name: str = Field(..., description="Permission name")
    description: str = Field(..., description="Permission description")


class Role(BaseModel):
    """
    Schema for user role.

    Attributes
    ----------
    name : str
        The name of the role.
    permissions : List[str]
        A list of permissions associated with the role.
    """
    name: str = Field(..., description="Role name")
    permissions: List[str] = Field(default_factory=list, description="List of permissions")



class UserBase(BaseModel):
    """
    Base schema for user data.

    Attributes
    ----------
    email : EmailStr
        The email address of the user.
    full_name : Optional[str]
        The full name of the user.
    """
    email: EmailStr = Field(..., description="User email address")
    full_name: Optional[str] = Field(None, description="User full name")

class UserCreate(UserBase):
    """
    Schema for creating a new user.

    Attributes
    ----------
    password : str
        The password for the new user.
    """
    password: str = Field(..., description="User password")

class UserLogin(BaseModel):
    """
    Schema for user login.

    Attributes
    ----------
    email : EmailStr
        The email address of the user.
    password : str
        The password of the user.
    """
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

class UserResponse(UserBase):
    """
    Schema for user response.

    Attributes
    ----------
    id : str
        A unique identifier for the user.
    created_at : datetime
        The timestamp when the user was created.
    updated_at : datetime
        The timestamp when the user was last updated.
    """
    id: str = Field(..., description="User ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        orm_mode = True