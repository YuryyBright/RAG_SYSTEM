from typing import List, Dict, Any, Optional

from modules.storage.document_store import DocumentStore
from domain.entities.document import Document
from domain.interfaces.reranking import RerankingService
from application.services.rag_context_retriever import RAGContextRetriever
from app.modules.reranking.factory import RerankerFactory
from domain.interfaces.embedding import EmbeddingInterface
from domain.interfaces.llm import LLMInterface


class RAGQueryProcessor:
    """
    Asynchronous processor for queries using Retrieval-Augmented Generation (RAG).

    Orchestrates embeddings, document retrieval, optional reranking,
    conversation context retrieval, and LLM response generation.

    Methods:
        process_query: Asynchronously executes the RAG pipeline for a query.
        _format_documents: Formats retrieved documents for the system prompt.
        _generate_system_prompt: Builds the LLM system prompt using contexts.
        _extract_snippet: Extracts a relevant snippet from document content.
        _rerank_documents: Reranks documents using a specified reranking service.
        extra_functionality: Placeholder for extending post-processing logic.
    """

    def __init__(
            self,
            document_store: DocumentStore,
            embedding_service: EmbeddingInterface,
            llm_provider: LLMInterface,
            reranking_service: Optional[RerankingService] = None,
            rag_context_retriever: Optional[RAGContextRetriever] = None,
            top_k: int = 5,
            reranker_type: Optional[str] = None,
    ):
        self.document_store = document_store
        self.embedding_service = embedding_service
        self.llm_provider = llm_provider
        self.reranking_service = reranking_service or RerankerFactory.get_reranker(reranker_type)
        self.rag_context_retriever = rag_context_retriever
        self.top_k = top_k

    async def process_query(
            self,
            query: Query,
            conversation_id: Optional[str] = None,
            theme_id: Optional[str] = None,
            reranker_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Asynchronously process a query using RAG, incorporating document
        retrieval, optional reranking, and conversation context.

        Args:
            query: The Query entity containing text to process.
            conversation_id: Optional conversation ID for context retrieval.
            theme_id: Optional theme ID to filter document search.
            reranker_type: Optional override for reranker type.

        Returns:
            A dict with:
                - query: original query text
                - response: generated LLM text
                - documents: metadata and snippet for each retrieved document
                - metadata: flags about context usage and counts
        """
        try:
            # 1. Embed Query
            query_embedding = await self.embedding_service.get_embedding(query.text)

            # 2. Retrieve documents via semantic search
            initial_docs = await self.document_store.semantic_search(
                query_embedding=query_embedding,
                limit=self.top_k * 3,
                theme_id=theme_id  # Larger pool of documents
            )

            if not initial_docs:
                return {
                    "query": query.text,
                    "response": "No relevant documents found.",
                    "documents": [],
                    "metadata": {
                        "document_count": 0,
                        "used_conversation_context": False,
                        "reranking_used": False,
                    },
                }

            # 3. Reranking
            reranking_used = False
            reranker = self.reranking_service

            if reranker_type and reranker_type != getattr(reranker, "reranker_type", None):
                reranker = RerankerFactory.get_reranker(reranker_type)

            min_score_threshold = 0.3  # Define threshold as a constant

            if reranker:
                reranked_docs, scores = await self._rerank_documents(query.text, initial_docs, reranker)
                # Filter weak documents
                reranked_docs = [doc for doc in reranked_docs if doc.score >= min_score_threshold]
                relevant_docs = reranked_docs[:self.top_k] if reranked_docs else initial_docs[:self.top_k]
                reranking_used = True
            else:
                # Apply similar filtering to non-reranked documents if they have scores
                filtered_docs = [doc for doc in initial_docs if getattr(doc, "score", 1.0) >= min_score_threshold]
                relevant_docs = filtered_docs[:self.top_k] if filtered_docs else initial_docs[:self.top_k]

            # 4. Prepare Document Context
            document_context = self._format_documents(relevant_docs)

            # 5. Optionally retrieve conversation context
            conversation_context = ""
            if conversation_id and self.rag_context_retriever:
                context_data = await self.rag_context_retriever.get_context_for_query(
                    conversation_id=conversation_id, query=query.text
                )
                conversation_context = self.rag_context_retriever.format_context_for_llm(context_data)

            # 6. Generate final prompt
            system_prompt = self._generate_system_prompt(conversation_context, document_context)

            # 7. Call LLM
            llm_response = await self.llm_provider.generate_text(
                system_prompt=system_prompt, user_prompt=query.text
            )

            # 8. Return all assembled information
            return {
                "query": query.text,
                "response": llm_response,
                "documents": [
                    {
                        "id": doc.id,
                        "title": doc.metadata.get("title", f"Document {idx + 1}"),
                        "source": doc.source or "Unknown",
                        "snippet": self._extract_snippet(doc.content, query.text),
                        "score": getattr(doc, "score", None)
                    }
                    for idx, doc in enumerate(relevant_docs)
                ],
                "metadata": {
                    "used_conversation_context": bool(conversation_context),
                    "document_count": len(relevant_docs),
                    "theme_id": theme_id,
                    "reranking_used": reranking_used,
                    "reranker_type": getattr(reranker, "reranker_type", None) if reranking_used else None
                },
            }
        except Exception as e:
            # Proper error handling
            import logging
            logging.error(f"Error processing query: {str(e)}", exc_info=True)
            return {
                "query": query.text,
                "response": "An error occurred while processing your query.",
                "documents": [],
                "metadata": {
                    "error": str(e),
                    "document_count": 0,
                    "used_conversation_context": False,
                    "reranking_used": False,
                },
            }

    async def _rerank_documents(
            self,
            query: str,
            documents: List[Document],
            reranking_service: RerankingService
    ) -> tuple[List[Document], List[float]]:
        """
        Rerank documents using the specified reranking service.

        Args:
            query: The query text
            documents: List of Document objects to rerank
            reranking_service: Service to use for reranking

        Returns:
            Tuple of (reranked document list, scores)
        """
        if not documents:
            return [], []

        document_texts = [doc.content for doc in documents]
        scores = await reranking_service.rerank(
            query=query,
            documents=document_texts,
            top_k=len(documents)
        )

        # Match scores with documents
        scored_docs = list(zip(documents, scores))
        # Sort by score in descending order
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        # Add score to document metadata and separate reranked docs from scores
        reranked_docs = []
        reranked_scores = []

        for doc, score in scored_docs:
            doc.metadata = doc.metadata or {}
            doc.metadata["rerank_score"] = score
            doc.score = score  # Add score directly to document for easy access
            reranked_docs.append(doc)
            reranked_scores.append(score)

        return reranked_docs, reranked_scores

    def _format_documents(self, documents: List[Document]) -> str:
        """
        Format a list of Document entities into a single string for the LLM.

        Returns a header plus each document's title and content.
        """
        if not documents:
            return "No relevant documents found."

        parts: List[str] = ["RELEVANT DOCUMENTS:"]
        for idx, doc in enumerate(documents, start=1):
            title = doc.metadata.get("title", f"Document {idx}")
            source = doc.source or "Unknown source"
            score_info = f" (Score: {doc.score:.4f})" if hasattr(doc, "score") else ""
            parts.append(f"[Document {idx}: {title} (Source: {source}){score_info}]")
            parts.append(doc.content)
            parts.append("")

        return "\n".join(parts)

    def _generate_system_prompt(
            self, conversation_context: str, document_context: str
    ) -> str:
        """
        Assemble the system prompt including guidelines, conversation history,
        and document excerpts.
        """
        base_instructions = [
            "You are a helpful assistant that answers questions based on the provided information.",
            "Always respond using only the information in the provided documents and conversation history.",
            "If the answer is not in the provided information, say you don't have enough information.",
            "Do not make up information."
        ]
        if conversation_context:
            base_instructions.append("\nCONVERSATION HISTORY:")
            base_instructions.append(conversation_context)

        base_instructions.append("\n" + document_context)
        return "\n".join(base_instructions)

    def _extract_snippet(self, text: str, query: str, max_length: int = 200) -> str:
        """
        Extract a relevant snippet up to `max_length` characters around query terms.

        Implements a sliding window to maximize query term coverage with better edge handling.
        """
        if len(text) <= max_length:
            return text

        query_terms = set(word.lower() for word in query.lower().split() if len(word) > 2)

        # If no significant query terms, return the beginning of the document
        if not query_terms:
            return text[:max_length] + ("..." if len(text) > max_length else "")

        text_lower = text.lower()
        best_start = 0
        best_score = 0
        window = max_length * 2  # Double-sized window for searching
        step = max(max_length // 4, 20)  # Smaller steps for better precision

        # Find the chunk with highest query term density
        for start in range(0, len(text_lower) - window + 1, step):
            chunk = text_lower[start:start + window]
            # Weight by both term presence and position in chunk
            score = sum(3 if term in chunk[:window // 2] else 1 for term in query_terms if term in chunk)
            if score > best_score:
                best_score = score
                best_start = start

        # Fine-tune to avoid cutting words
        adjusted_start = best_start
        if best_start > 0:
            # Find word boundary to the right
            space_pos = text.find(' ', best_start)
            if space_pos > 0 and space_pos < best_start + 20:  # Don't move too far
                adjusted_start = space_pos + 1

        snippet = text[adjusted_start:adjusted_start + max_length]

        # Adjust to word boundaries
        if adjusted_start > 0:
            snippet = "..." + snippet.lstrip()
        if adjusted_start + max_length < len(text):
            last_space = snippet.rfind(' ')
            if last_space > max_length * 0.75:  # Only truncate if we keep most of the content
                snippet = snippet[:last_space] + "..."
            else:
                snippet = snippet.rstrip() + "..."

        return snippet