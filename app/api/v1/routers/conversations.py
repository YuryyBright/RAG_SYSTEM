from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session

from api.middleware_auth import get_current_active_user
from app.api.schemas.conversation import (
    ConversationCreate, ConversationUpdate, ConversationResponse,
    ConversationDetailResponse, MessageCreate, MessageResponse, ConversationContextResponse, RerankingConfig
)

from app.api.dependencies.dependencies import get_conversation_service, get_context_service, get_rag_context_retriever
from application.services.context_management_service import ContextManagementService
from application.services.conversation_service import ConversationService
from infrastructure.repositories.repository import get_async_db

router = APIRouter()


@router.post("", response_model=ConversationResponse)
async def create_conversation(
        conversation: ConversationCreate,
        db: Session = Depends(get_async_db),
        current_user=Depends(get_current_active_user),
        conversation_service: ConversationService = Depends(get_conversation_service)
):
    """Create a new conversation."""
    return conversation_service.create_conversation(
        user_id=current_user.id,
        title=conversation.title,
        theme_id=conversation.theme_id,
        model_id=conversation.model_id,
        metadata=conversation.metadata
    )


@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
        active_only: bool = Query(False, description="Filter only active conversations"),
        db: Session = Depends(get_async_db),
        current_user=Depends(get_current_active_user),
        conversation_service: ConversationService = Depends(get_conversation_service)
):
    """Get all conversations for the current user."""
    return conversation_service.get_user_conversations(
        user_id=current_user.id,
        active_only=active_only
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
        conversation_id: str = Path(..., description="The ID of the conversation to get"),
        db: Session = Depends(get_async_db),
        current_user=Depends(get_current_active_user),
        conversation_service: ConversationService = Depends(get_conversation_service)
):
    """Get a specific conversation with its messages."""
    conversation = await conversation_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this conversation")

    # Get messages for this conversation
    messages = await conversation_service.get_messages(conversation_id)

    # Create the response with conversation and messages
    response = ConversationDetailResponse.from_orm(conversation)
    response.messages = [MessageResponse.from_orm(msg) for msg in messages]

    return response


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
        conversation_update: ConversationUpdate,
        conversation_id: str = Path(..., description="The ID of the conversation to update"),
        db: Session = Depends(get_async_db),
        current_user=Depends(get_current_active_user),
        conversation_service: ConversationService = Depends(get_conversation_service)
):
    """Update a conversation."""
    # First check if the conversation exists and belongs to the current user
    conversation = await conversation_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this conversation")

    # Update the conversation
    updated_conversation = await conversation_service.update_conversation(
        conversation_id=conversation_id,
        title=conversation_update.title,
        is_active=conversation_update.is_active,
        metadata=conversation_update.metadata
    )

    return updated_conversation


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
        conversation_id: str = Path(..., description="The ID of the conversation to delete"),
        db: Session = Depends(get_async_db),
        current_user=Depends(get_current_active_user),
        conversation_service: ConversationService = Depends(get_conversation_service)
):
    """Delete a conversation."""
    # First check if the conversation exists and belongs to the current user
    conversation = await conversation_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this conversation")

    # Delete the conversation
    success = await conversation_service.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete conversation")


@router.post("/{conversation_id}/reranking-config", response_model=ConversationResponse)
async def update_reranking_config(
        reranking_config: RerankingConfig,
        conversation_id: str = Path(..., description="The ID of the conversation"),
        db: Session = Depends(get_async_db),
        current_user=Depends(get_current_active_user),
        conversation_service: ConversationService = Depends(get_conversation_service)
):
    """Update reranking configuration for a conversation."""
    # Check authorization
    conversation = await conversation_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this conversation")

    # Update metadata with reranking config
    metadata = conversation.metadata or {}
    metadata["reranking"] = {
        "enabled": reranking_config.enabled,
        "method": reranking_config.method,
        "top_k": reranking_config.top_k
    }

    # Update conversation with new metadata
    updated_conversation = await conversation_service.update_conversation(
        conversation_id=conversation_id,
        metadata=metadata
    )

    return updated_conversation
@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def add_message(
        message: MessageCreate,
        conversation_id: str = Path(..., description="The ID of the conversation"),
        db: Session = Depends(get_async_db),
        current_user=Depends(get_current_active_user),
        conversation_service: ConversationService = Depends(get_conversation_service),
        context_service: ContextManagementService = Depends(get_context_service)
):
    """Add a message to a conversation."""
    # First check if the conversation exists and belongs to the current user
    conversation = await conversation_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to add messages to this conversation")

    # Add the message
    new_message = await conversation_service.add_message(
        conversation_id=conversation_id,
        role=message.role,
        content=message.content,
        is_hidden=message.is_hidden,
        references=message.references,
        metadata=message.metadata
    )

    # Update context for the conversation (asynchronously in a real implementation)
    if message.role == "user" or message.role == "assistant":
        # Create message context
        await context_service.create_context(
            conversation_id=conversation_id,
            content=message.content,
            context_type="message",
            priority=3 if message.role == "assistant" else 2
        )

        # Check if we need to maintain the context window
        await context_service.maintain_context_window(conversation_id)

        # Every 10 messages, create a summary
        messages = await conversation_service.get_messages(conversation_id)
        if len(messages) % 10 == 0:
            await context_service.summarize_conversation(conversation_id)
            await context_service.extract_key_points(conversation_id)

    return new_message


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def list_messages(
        conversation_id: str = Path(..., description="The ID of the conversation"),
        include_hidden: bool = Query(False, description="Include hidden system messages"),
        db: Session = Depends(get_async_db),
        current_user=Depends(get_current_active_user),
        conversation_service: ConversationService = Depends(get_conversation_service)
):
    """Get all messages for a conversation."""
    # First check if the conversation exists and belongs to the current user
    conversation = await conversation_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this conversation")

    # Get messages
    messages = await conversation_service.get_messages(
        conversation_id=conversation_id,
        include_hidden=include_hidden
    )

    return messages


@router.get("/{conversation_id}/history", response_model=ConversationResponse)
async def get_chat_history(
        conversation_id: str = Path(..., description="The ID of the conversation"),
        db: Session = Depends(get_async_db),
        current_user=Depends(get_current_active_user),
        conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    Get a conversation history summary (stats, activity dates, etc.).
    """
    conversation = await conversation_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this conversation")

    stats = await conversation_service.get_conversation_stats(conversation_id)
    return stats

@router.get("/{conversation_id}/context", response_model=ConversationContextResponse)
async def get_conversation_context(
        conversation_id: str = Path(..., description="The ID of the conversation"),
        query: Optional[str] = Query(None, description="Optional query to retrieve semantic context"),
        db: Session = Depends(get_async_db),
        current_user=Depends(get_current_active_user),
        rag_context_retriever=Depends(get_rag_context_retriever),
        conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    Retrieve RAG context (recent messages, semantic contexts, summaries) for a conversation.
    """
    conversation = await conversation_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this conversation")

    query = query or "general"  # fallback for relevance
    context_data = await rag_context_retriever.get_context_for_query(conversation_id, query=query)
    return context_data

@router.get("/history", response_model=List[ConversationResponse])
async def get_user_chat_history(
        active_only: bool = Query(False, description="Filter only active conversations"),
        limit: Optional[int] = Query(None, description="Maximum number of conversations to return"),
        offset: Optional[int] = Query(None, description="Number of conversations to skip"),
        current_user=Depends(get_current_active_user),
        conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    Get conversation history for the current user (optionally active-only).
    """
    conversations = await conversation_service.get_user_conversations(
        user_id=current_user.id,
        active_only=active_only,
        limit=limit,
        offset=offset
    )
    return conversations