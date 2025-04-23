from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, UploadFile, Request
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import JSONResponse

from api.dependencies.ai_dependencies import get_conversation_service, get_context_service, get_rag_context_retriever, \
    get_llm_service
from api.dependencies.document_dependency import get_document_store
from api.middleware_auth import get_current_active_user
from app.api.schemas.conversation import (
    ConversationCreate, ConversationUpdate, ConversationResponse,
    ConversationDetailResponse, MessageCreate, MessageResponse, ConversationContextResponse, RerankingConfig, ModelInfo,
    ChatResponse, ConversationStatsResponse
)

from application.services.context_management_service import ContextManagementService
from application.services.conversation_service import ConversationService
from application.services.rag_context_retriever import RAGContextRetriever
from core.use_cases.query import RAGQueryProcessor
from domain.interfaces.embedding import EmbeddingInterface
from infrastructure.repositories import get_async_db
from modules.embeding.embedding_factory import get_embedding_service
from modules.llm import LLMFactory
from modules.storage.document_store import DocumentStore

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
        metadata=conversation.metadata_dict
    )


@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
        active_only: bool = Query(False, description="Filter only active conversations"),
        db: Session = Depends(get_async_db),
        current_user=Depends(get_current_active_user),
        conversation_service: ConversationService = Depends(get_conversation_service)
):
    """Get all conversations for the current user."""
    return await conversation_service.get_user_conversations(
        user_id=current_user.id,
        active_only=active_only
    )
@router.get("/models", summary="List available LLM models", response_model=List[ModelInfo])
async def list_available_models(
    current_user=Depends(get_current_active_user),
    llm_services = Depends(get_llm_service)
) -> List[ModelInfo]:
    models = llm_services.list_available_models()
    model_infos = []

    for idx, model in enumerate(models):
        model_info = ModelInfo(
            id=str(idx),  # Generate a dummy ID (you can improve this later)
            name=model["name"],
            provider=model.get("type", "unknown"),  # map 'type' as 'provider'
            file_path=model["file_path"],
            size=model["size"]
        )
        model_infos.append(model_info)

    return model_infos

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

async def _extract_body(request: Request) -> Dict[str, Any]:
    """Parse incoming request supporting both JSON & multipart bodies."""
    if request.headers.get("content-type", "").startswith("application/json"):
        return await request.json()

    form = await request.form()
    # Starlette returns UploadFile objects for files key (may be multiple)
    body: Dict[str, Any] = dict(form)
    # Flatten single value lists (except files)
    files = [f for f in body.get("files", []) if isinstance(f, UploadFile)]
    if files:
        body["files"] = files
    return body


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(
        request: Request,
        conversation_service: ConversationService = Depends(get_conversation_service),
        context_management_service: ContextManagementService = Depends(get_context_service),
        embedding_service: EmbeddingInterface = Depends(get_embedding_service),
        llm_services = Depends(get_llm_service),
        document_store: DocumentStore = Depends(get_document_store),
        current_user=Depends(get_current_active_user),
        rag_context_retriever= Depends(get_rag_context_retriever),
):
    """Main chat endpoint used by the front‑end `sendMessage()` function."""

    body = await _extract_body(request)

    message: str | None = body.get("message")
    files: List[UploadFile] = body.get("files") or []
    rag_mode: bool = str(body.get("rag_mode", "false")).lower() == "true"
    conversation_id: Optional[str] = body.get("conversation_id")
    theme_id: Optional[str] = body.get("theme_id")
    model_id: Optional[str] = body.get("model_id")

    # Accept additional advanced params transparently
    custom_params: Dict[str, Any] = {
        k: v for k, v in body.items()
        if k not in {"message", "files", "rag_mode", "conversation_id", "theme_id", "model_id"}
    }

    if not message and not files:
        raise HTTPException(status_code=400, detail="No message content or files provided")

    # 1. Ensure conversation exists / belongs to user
    if conversation_id:
        conversation = await conversation_service.get_conversation(conversation_id)
        if not conversation or conversation.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized for this conversation")
    else:
        conversation = await conversation_service.create_conversation(
            user_id=current_user.id,
            theme_id=theme_id,
            model_id=model_id,
        )
        conversation_id = conversation.id

    # 2. Persist user message
    await conversation_service.add_message(
        conversation_id=conversation_id,
        role="user",
        content=message or "[user sent attachments]",
        metadata={"files": [f.filename for f in files]} if files else None,
    )

    # 3. Create RAG context retriever and query processor when in RAG mode
    if model_id is not None and model_id.isdigit():
        # Convert index to model name
        models = llm_services.list_available_models()
        index = int(model_id)
        if 0 <= index < len(models):
            model_id = models[index]["name"]
        else:
            # Handle invalid index
            model_id = None  # Use default model
    llm_service = llm_services.get_llm(model_id)

    # Initialize response variables
    assistant_response = ""
    result = {"documents": [], "metadata": {}}

    if rag_mode:
        # Initialize RAG components

        query_processor = RAGQueryProcessor(
            document_store=document_store,
            embedding_service=embedding_service,
            llm_provider=llm_service,
            rag_context_retriever=rag_context_retriever,
            top_k=5,  # Configurable parameter
        )

        # 4. Process query with RAG pipeline
        from domain.entities.document import Query  # Import the Query entity

        result = await query_processor.process_query(
            Query(text=message or ""),
            conversation_id=conversation_id,
            theme_id=theme_id,
        )

        assistant_response = result["response"]
    else:
        # Regular non-RAG conversation flow
        # Get conversation context
        context_messages = await conversation_service.get_messages(
            conversation_id=conversation_id,
            limit=10  # Get recent messages for context
        )

        # Format conversation history for the LLM
        conversation_context = "\n".join([
            f"{msg.role}: {msg.content}"
            for msg in context_messages
            if not msg.is_hidden
        ])

        # Create system prompt
        system_prompt = (
            "You are a helpful assistant responding to user queries. "
            "Consider the conversation history for context when appropriate."
        )

        if conversation_context:
            system_prompt += f"\n\nConversation history:\n{conversation_context}"

        # Generate response
        assistant_response = await llm_service.generate_text(
            system_prompt=system_prompt,
            prompt=message or ""
        )

    # 5. Persist assistant message
    await conversation_service.add_message(
        conversation_id=conversation_id,
        role="assistant",
        content=assistant_response.get("text", ""),
        metadata={"documents": result.get("documents", [])} if rag_mode else None,
    )

    # 6. Update conversation context when using RAG
    if rag_mode and message:
        await context_management_service.create_context(
            conversation_id=conversation_id,
            content=f"User: {message}\nAssistant: {assistant_response}",
            context_type="message_pair"
        )

        # Maintain context window periodically
        await context_management_service.maintain_context_window(conversation_id)

    # 7. Build transport response
    payload: Dict[str, Any] = {
        "conversation_id": conversation_id,
        "response": assistant_response.get("text", "") if isinstance(assistant_response, dict) else str(assistant_response),
        "documents": result.get("documents", []) if rag_mode else [],
        "metadata": {
            **result.get("metadata", {}),
            "rag_mode": rag_mode,
        },
    }

    # Optionally include custom params back for the front‑end
    if custom_params:
        payload["echo"] = custom_params

    return JSONResponse(content=payload, status_code=200)

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
    metadata = conversation.metadata_dict or {}
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


@router.get("/{conversation_id}/history", response_model=ConversationDetailResponse)
async def get_chat_history(
        conversation_id: str = Path(..., description="The ID of the conversation"),
        db: Session = Depends(get_async_db),
        current_user=Depends(get_current_active_user),
        conversation_service: ConversationService = Depends(get_conversation_service)
):
    conversation = await conversation_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this conversation")

    stats = await conversation_service.get_conversation_stats(conversation_id)

    # Wrap the extra fields into a `settings` object for frontend compatibility
    return ConversationDetailResponse(
        id=stats["id"],
        title=stats["title"],
        user_id=stats["user_id"],
        created_at=stats["created_at"],
        updated_at=stats["updated_at"],
        is_active=stats["is_active"],
        theme_id=stats["theme_id"],
        model_id=stats["model_id"],
        conversation_metadata=stats.get("metadata"),
        messages=[MessageResponse.from_orm(msg) for msg in stats["messages"]]
    )


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


# @router.get("/history", response_model=List[ConversationResponse])
# async def get_user_chat_history(
#     active_only: bool = Query(False, description="Filter only active conversations"),
#     limit: Optional[int] = Query(None, description="Maximum number of conversations to return"),
#     offset: Optional[int] = Query(None, description="Number of conversations to skip"),
#     current_user=Depends(get_current_active_user),
#     conversation_service: ConversationService = Depends(get_conversation_service)
# ):
#     """
#     Get conversation history for the current user (optionally active-only).
#     """
#     conversations = await conversation_service.get_user_conversations(
#         user_id=current_user.id,
#         active_only=active_only,
#         limit=limit,
#         offset=offset
#     )
#
#     # Explicitly handle empty list — DO NOT raise 404
#     if conversations is None:
#         return []
#
#     return conversations