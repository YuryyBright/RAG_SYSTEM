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
    message_metadata: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True
        from_attributes = True


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
    conversation_metadata: dict[str, Any] | None = None

    class Config:
        orm_mode = True

class ConversationStatsResponse(BaseModel):
    message_count: int
    role_distribution: Dict[str, int]
    total_tokens: int
    first_message: Optional[str]
    last_message: Optional[str]
    theme_id: Optional[str]
    model_id: Optional[str]
    is_active: bool
    metadata: Optional[Dict[str, Any]]


class RerankingConfig(BaseModel):
    enabled: bool = True
    method: str = "cross-encoder"  # Options: "cross-encoder", "bm25"
    top_k: int = 5  # Number of results to keep after reranking

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
    file_path : str
        The provider of the model (e.g., OpenAI, HuggingFace).
    size : int | None, optional
        The maximum context window size supported by the model, if applicable.
    """
    id: str
    name: str
    provider: str
    file_path: str
    size: int
    #context_window: int | None = None


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


class DocumentInfo(BaseModel):
    """Information about a document retrieved by RAG."""
    id: str
    title: str
    source: str
    snippet: str
    score: Optional[float] = None


class MetadataInfo(BaseModel):
    """Metadata about the chat response."""
    used_conversation_context: Optional[bool] = False
    document_count: Optional[int] = 0
    theme_id: Optional[str] = None
    reranking_used: Optional[bool] = False
    reranker_type: Optional[str] = None
    rag_mode: Optional[bool] = False
    error: Optional[str] = None


class ChatResponse(BaseModel):
    """Response model for the chat endpoint."""
    conversation_id: str
    response: str
    documents: List[DocumentInfo] = Field(default_factory=list)
    metadata: MetadataInfo = Field(default_factory=MetadataInfo)
    echo: Optional[Dict[str, Any]] = None