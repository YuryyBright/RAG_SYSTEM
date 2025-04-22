# app/adapters/reranking/factory.py
from typing import Optional

from adapters.reranking.cross_encoder import CrossEncoderReranker
from app.core.interfaces.reranking import RerankingService
from app.adapters.reranking.bm25_reranker import BM25Reranker
from app.config import settings


class RerankerFactory:
    """
    Factory class for creating reranker instances.
    """

    @staticmethod
    def get_reranker(reranker_type: Optional[str] = None) -> RerankingService:
        """
        Get a reranker instance based on type.

        Args:
            reranker_type: The type of reranker to create.
                Options: 'cross-encoder', 'bm25', or None (uses default from settings).

        Returns:
            An instance of a RerankingService.

        Raises:
            ValueError: If the reranker type is not supported.
        """
        reranker_type = reranker_type or getattr(settings, 'RERANKER_TYPE', 'bm25')

        if reranker_type == 'cross-encoder':
            model_name = getattr(settings, 'CROSS_ENCODER_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
            return CrossEncoderReranker(model_name=model_name)
        elif reranker_type == 'bm25':
            return BM25Reranker()
        else:
            raise ValueError(f"Unsupported reranker type: {reranker_type}")