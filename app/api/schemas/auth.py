from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr

class LoginRequest(BaseModel):
    """
    Schema for user login request.
    Schema for user login request.

    Attributes
    ----------
    email : EmailStr
        The email address of the user.
    password : str
        The password of the user.
    """
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class LoginResponse(BaseModel):
    """
    Schema for user login request.

    Attributes
    ----------
    email : EmailStr
        The email address of the user.
    password : str
        The password of the user.
    """
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

class TokenData(BaseModel):
    """
    Schema for token data.

    Attributes
    ----------
    username : Optional[str]
        The username of the user associated with the token.
    """
    username: Optional[str] = Field(None, description="User username")

class TokenResponse(BaseModel):
    """
    Schema for token response.

    Attributes
    ----------
    access_token : str
        The JWT access token.
    token_type : str
        The type of the token, typically "Bearer".
    expires_at : datetime
        The expiration time of the token.
    user_id : str
        The ID of the user associated with the token.
    username : str
        The username of the user associated with the token.
    """
    access_token: str
    token_type: str
    expires_at: datetime
    user_id: str
    username: str