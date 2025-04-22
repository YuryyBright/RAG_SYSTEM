# app/adapters/reranking/cross_encoder_reranker.py
import numpy as np
from typing import List, Optional, Dict, Any, Tuple
from app.core.interfaces.reranking import RerankingService


class CrossEncoderReranker(RerankingService):
    """
    A reranking service implementation using a cross-encoder model.

    Cross-encoders score query-document pairs as a single input for more accurate
    relevance scoring than bi-encoders used in initial retrieval.

    Attributes:
        model: The cross-encoder model for scoring query-document pairs.
        tokenizer: The tokenizer for the model.
        max_length: Maximum input sequence length.
        device: The computation device to use.
    """

    def __init__(
            self,
            model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
            max_length: int = 512,
            batch_size: int = 8,
            device: str = "cpu"
    ):
        """
        Initialize the CrossEncoderReranker.

        Args:
            model_name: The name of the cross-encoder model.
            max_length: Maximum input sequence length.
            batch_size: Batch size for processing multiple documents.
            device: The device to use for computations ('cpu' or 'cuda').
        """
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(model_name, max_length=max_length, device=device)
            self.batch_size = batch_size
        except ImportError:
            raise ImportError(
                "CrossEncoderReranker requires sentence-transformers. "
                "Install with: pip install sentence-transformers"
            )

    async def rerank(
            self,
            query: str,
            documents: List[str],
            top_k: Optional[int] = None
    ) -> List[int]:
        """
        Rerank documents based on their relevance to the query.

        Args:
            query: The query text.
            documents: List of document contents to rerank.
            top_k: The number of top documents to return (default: all documents).

        Returns:
            List of indices of the original documents, ordered by relevance.
        """
        if not documents:
            return []

        # Prepare query-document pairs for scoring
        pairs = [(query, doc) for doc in documents]

        # Score the pairs using the cross-encoder model
        scores = self.model.predict(pairs)

        # Sort document indices by scores in descending order
        sorted_indices = np.argsort(scores)[::-1]

        # Return top-k indices if specified
        if top_k is not None:
            sorted_indices = sorted_indices[:min(top_k, len(sorted_indices))]

        return sorted_indices.tolist()