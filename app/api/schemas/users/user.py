from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime

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