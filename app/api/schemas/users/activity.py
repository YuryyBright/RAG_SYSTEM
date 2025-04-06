from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

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


from pydantic import BaseModel, Field
from typing import List

class ActivityLogResponse(BaseModel):
    """
    Schema for user activity log response.

    Attributes
    ----------
    activities : List[ActivityLogEntry]
        A list of activity log entries.
    """
    activities: List[ActivityLogEntry] = Field(default_factory=list, description="List of activity log entries")