# app/core/services/rag_context_retriever.py

from domain.interfaces.reranking import RerankingService
from app.modules.reranking.factory import RerankerFactory


class RAGContextRetriever:
    def __init__(
            self,
            vector_index_service,
            context_service,
            conversation_service,
            reranker: RerankingService = None
    ):
        self.vector_index_service = vector_index_service
        self.context_service = context_service
        self.conversation_service = conversation_service
        # Get default reranker if not provided
        self.reranker = reranker or RerankerFactory.get_reranker()

    async def get_context_for_query(self, conversation_id, query):
        # 1. Get recent messages
        recent_messages = await self.conversation_service.get_recent_messages(conversation_id, limit=5)

        # 2. Get semantic search results
        theme_id = await self._get_theme_id_for_conversation(conversation_id)
        semantic_results = []
        if theme_id:
            # Get initial results from vector store
            initial_results = await self.vector_index_service.search(
                query=query,
                theme_id=theme_id,
                limit=10  # Get more than we need for reranking
            )

            # Apply reranking to the results
            if initial_results and len(initial_results) > 0:
                reranked_results = self.reranker.rerank(
                    query=query,
                    documents=[doc.content for doc in initial_results],
                    metadata=[doc.metadata for doc in initial_results]
                )

                # Keep only top N results after reranking
                semantic_results = reranked_results[:5]  # Adjust number as needed

        # 3. Get conversation contexts
        context_items = await self.context_service.get_conversation_context(conversation_id)

        # 4. Compile all contexts
        return {
            "recent_messages": recent_messages,
            "semantic_results": semantic_results,
            "context_items": context_items
        }

    async def _get_theme_id_for_conversation(self, conversation_id):
        # Get theme_id from conversation
        conversation = await self.conversation_service.get_conversation(conversation_id)
        return conversation.theme_id if conversation else None