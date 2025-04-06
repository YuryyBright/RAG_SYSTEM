from typing import List, Dict, Any
from api.core.interfaces.embedding import EmbeddingInterface
from api.core.interfaces.indexing import IndexInterface
from api.core.interfaces.llm import LLMInterface
from api.core.interfaces.reranking import RerankerInterface

class QueryProcessor:
    """
    Use case for processing user queries against indexed documents.

    This class handles the process of embedding a query, retrieving similar documents,
    reranking them based on relevance, and generating a response using a large language model.

    Attributes
    ----------
    embedding_service : EmbeddingInterface
        Service for generating embeddings for queries.
    index_service : IndexInterface
        Service for indexing and searching documents.
    reranker_service : RerankerInterface
        Service for reranking retrieved documents.
    llm_service : LLMInterface
        Service for generating responses using a large language model.
    score_threshold : float
        Minimum score threshold for considering a document relevant.
    """

    def __init__(
        self,
        embedding_service: EmbeddingInterface,
        index_service: IndexInterface,
        reranker_service: RerankerInterface,
        llm_service: LLMInterface,
        score_threshold: float = 0.35
    ):
        self.embedding_service = embedding_service
        self.index_service = index_service
        self.reranker_service = reranker_service
        self.llm_service = llm_service
        self.score_threshold = score_threshold

    async def process_query(
        self,
        query: str,
        top_k: int = 5,
        rerank_top_k: int = 3
    ) -> Dict[str, Any]:
        """
        Process a user query and return an answer with supporting context.

        Parameters
        ----------
        query : str
            The user's question.
        top_k : int, optional
            Number of initial documents to retrieve (default is 5).
        rerank_top_k : int, optional
            Number of documents to keep after reranking (default is 3).

        Returns
        -------
        Dict[str, Any]
            Dictionary with the answer and metadata about the sources.
        """
        # Embed the query
        query_embedding = await self.embedding_service.embed_query(query)

        # Retrieve similar documents
        search_results = await self.index_service.search(query_embedding, k=top_k)

        # Rerank the results
        reranked_results = await self.reranker_service.rerank(
            query=query,
            documents=search_results,
            top_k=rerank_top_k
        )

        # Check if top result meets threshold
        if not reranked_results or reranked_results[0].get("score", 0) < self.score_threshold:
            return {
                "answer": "I don't know enough to answer this question based on the available documents.",
                "sources": [],
                "has_answer": False
            }

        # Generate answer using LLM with context
        prompt = self._create_prompt(query, reranked_results)
        answer = await self.llm_service.generate(prompt, reranked_results)

        return {
            "answer": answer,
            "sources": [
                {
                    "id": doc.get("id"),
                    "metadata": doc.get("metadata", {}),
                    "score": doc.get("score", 0)
                }
                for doc in reranked_results
            ],
            "has_answer": True
        }

    def _create_prompt(self, query: str, context: List[Dict[str, Any]]) -> str:
        """
        Create a prompt for the LLM based on the query and context.

        Parameters
        ----------
        query : str
            The user's question.
        context : List[Dict[str, Any]]
            A list of dictionaries representing the context documents.

        Returns
        -------
        str
            The generated prompt for the LLM.
        """
        context_text = "\n\n".join([
            f"Document {i + 1}:\n{doc.get('content', '')}"
            for i, doc in enumerate(context)
        ])

        return f"""Answer the question based ONLY on the following context. If the context doesn't contain enough information to answer the question, respond with "I don't know.".

                Context:
                {context_text}
                
                Question: {query}
                
                Answer:"""
