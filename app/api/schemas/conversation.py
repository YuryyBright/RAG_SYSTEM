from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    role: str = Field(..., description="Role of the message sender (user, assistant, system)")
    content: str = Field(..., description="Content of the message")
    is_hidden: bool = Field(False, description="Flag indicating if the message should be hidden from UI")
    references: Optional[List[Dict[str, Any]]] = Field(None, description="Document references used for this message")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional message metadata")


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: datetime
    tokens: int
    is_hidden: bool
    references: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True


class ConversationCreate(BaseModel):
    title: str = Field("New Conversation", description="Title of the conversation")
    theme_id: Optional[str] = Field(None, description="ID of the knowledge theme for this conversation")
    model_id: Optional[str] = Field(None, description="ID of the AI model to use")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional conversation metadata")


class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Title of the conversation")
    is_active: Optional[bool] = Field(None, description="Flag indicating if the conversation is active")
    theme_id: Optional[str] = Field(None, description="ID of the knowledge theme for this conversation")
    model_id: Optional[str] = Field(None, description="ID of the AI model to use")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional conversation metadata")


class ConversationResponse(BaseModel):
    id: str
    title: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    is_active: bool
    theme_id: Optional[str] = None
    model_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True


class ConversationDetailResponse(ConversationResponse):
    messages: List[MessageResponse] = []

    class Config:
        orm_mode = True


class ModelInfo(BaseModel):
    """
    Represents information about a model.

    Attributes
    ----------
    id : str
        The unique identifier of the model.
    name : str
        The name of the model.
    provider : str
        The provider of the model (e.g., OpenAI, HuggingFace).
    context_window : int | None, optional
        The maximum context window size supported by the model, if applicable.
    """
    id: str
    name: str
    provider: str
    context_window: int | None = None


class ConversationContextResponse(BaseModel):
    """
    Represents the response for a conversation context.

    Attributes
    ----------
    id : str
        The unique identifier of the context.
    type : str
        The type of the context (e.g., message, summary).
    content : str
        The content of the context.
    priority : int
        The priority level of the context.
    updated_at : datetime
        The timestamp when the context was last updated.
    """
    id: str
    type: str
    content: str
    priority: int
    updated_at: datetime