from pydantic import BaseModel, Field
from typing import List
from pydantic import BaseModel, Field
from datetime import datetime


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