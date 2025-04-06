from pydantic import BaseModel, Field

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