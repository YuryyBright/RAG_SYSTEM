"""
This module defines the QueryProcessor class which orchestrates the RAG pipeline.

The QueryProcessor coordinates between embedding, indexing, reranking, and LLM services
to process user queries and generate relevant responses based on retrieved documents.
"""

from typing import List, Dict, Any, Optional

from app.core.interfaces.embedding import EmbeddingInterface
from app.core.interfaces.indexing import IndexInterface
from app.core.interfaces.llm import LLMInterface
from app.core.interfaces.reranking import RerankerInterface
from app.core.entities.document import Document
from app.core.entities.query import Query


class QueryProcessor:
    """
    QueryProcessor orchestrates the RAG (Retrieval-Augmented Generation) pipeline.

    It handles:
    1. Converting user queries to embeddings
    2. Retrieving relevant documents from the index
    3. Reranking results for better relevance
    4. Generating responses using an LLM with retrieved context
    """

    def __init__(
            self,
            embedding_service: EmbeddingInterface,
            index_service: IndexInterface,
            reranker_service: RerankerInterface,
            llm_service: LLMInterface,
            score_threshold: float = 0.5,
            max_docs: int = 10
    ):
        """
        Initialize the QueryProcessor with necessary services.

        Args:
            embedding_service: Service for generating embeddings from text
            index_service: Service for indexing and retrieving documents
            reranker_service: Service for reranking retrieved documents
            llm_service: Service for generating responses with LLM
            score_threshold: Minimum similarity score for retrieved documents
            max_docs: Maximum number of documents to retrieve
        """
        self.embedding_service = embedding_service
        self.index_service = index_service
        self.reranker_service = reranker_service
        self.llm_service = llm_service
        self.score_threshold = score_threshold
        self.max_docs = max_docs

    async def process_query(self, query: Query) -> Dict[str, Any]:
        """
        Process a user query through the RAG pipeline.

        Args:
            query: The user query object

        Returns:
            Dict containing the LLM response and relevant context information
        """
        # Generate embedding for the query
        query_embedding = await self.embedding_service.embed_query(query.text)

        # Retrieve relevant documents from index
        retrieved_docs = await self.index_service.search(
            query_embedding,
            limit=self.max_docs
        )

        # Filter documents by score threshold
        filtered_docs = [
            doc for doc in retrieved_docs
            if doc["score"] >= self.score_threshold
        ]

        if not filtered_docs:
            # If no documents meet the threshold, return a generic response
            return {
                "answer": "I couldn't find relevant information to answer your question.",
                "sources": [],
                "context": []
            }

        # Rerank documents with cross-encoder for better relevance
        reranked_docs = await self.reranker_service.rerank(
            query=query.text,
            documents=[doc["document"] for doc in filtered_docs]
        )

        # Extract text from top documents to use as context
        context_texts = [doc.content for doc in reranked_docs]
        context = "\n\n".join(context_texts)

        # Generate response from LLM using retrieved context
        llm_response = await self.llm_service.generate_response(
            query=query.text,
            context=context
        )

        # Prepare source information for citation
        sources = [
            {
                "id": doc.id,
                "title": doc.title,
                "url": doc.url,
                "score": doc.score
            }
            for doc in reranked_docs
        ]

        return {
            "answer": llm_response,
            "sources": sources,
            "context": context_texts
        }

    async def process_followup_query(
            self,
            query: Query,
            conversation_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Process a follow-up query with conversation history.

        Args:
            query: The user follow-up query
            conversation_history: Previous Q&A pairs in the conversation

        Returns:
            Dict containing the LLM response and relevant context information
        """
        # Generate embedded query with conversation context
        conversation_context = "\n".join(
            [f"Q: {item['question']}\nA: {item['answer']}"
             for item in conversation_history]
        )

        # Create an augmented query with conversation history
        augmented_query = f"{conversation_context}\n\nFollow-up Q: {query.text}"

        # Create a new query object with the augmented text
        contextual_query = Query(text=augmented_query, user_id=query.user_id)

        # Process using the standard pipeline
        return await self.process_query(contextual_query)