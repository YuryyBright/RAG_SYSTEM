from pydantic import BaseModel, Field
from typing import List

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