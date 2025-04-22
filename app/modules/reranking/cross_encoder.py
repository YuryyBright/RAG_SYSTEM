# app/modules/reranking/cross_encoder.py
from typing import List, Dict, Any, Optional
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from domain.interfaces.reranking import RerankingService
from app.utils.logger_util import get_logger

logger = get_logger(__name__)


class CrossEncoderReranker(RerankingService):
    """
    Reranker using Cross-Encoder models from HuggingFace.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize the Cross-Encoder reranker with the specified model.

        Parameters
        ----------
        model_name : str, optional
            The name of the cross-encoder model, by default "cross-encoder/ms-marco-MiniLM-L-6-v2"
        """
        self.model_name = model_name
        logger.info(f"Loading Cross-Encoder model: {model_name}")

        # Load model and tokenizer
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model.to(self.device)

        logger.info(f"Cross-Encoder model loaded on {self.device}")

    def rerank(
            self,
            query: str,
            documents: List[str],
            metadata: Optional[List[Dict[str, Any]]] = None,
            top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents using the cross-encoder model.

        Parameters
        ----------
        query : str
            The query text
        documents : List[str]
            List of document texts to rerank
        metadata : Optional[List[Dict[str, Any]]], optional
            List of metadata for each document, by default None
        top_k : Optional[int], optional
            Number of top results to return, by default None

        Returns
        -------
        List[Dict[str, Any]]
            Reranked documents with scores
        """
        if not documents:
            return []

        # Create pairs of query and documents
        pairs = [[query, doc] for doc in documents]

        # Encode and get scores
        with torch.no_grad():
            inputs = self.tokenizer(
                pairs,
                padding=True,
                truncation=True,
                return_tensors="pt",
                max_length=512
            ).to(self.device)

            scores = self.model(**inputs).logits.flatten().cpu().numpy()

        # Create result with document, score, and metadata
        results = []
        for i, (doc, score) in enumerate(zip(documents, scores)):
            result = {
                "content": doc,
                "score": float(score),
                "metadata": metadata[i] if metadata else {}
            }
            results.append(result)

        # Sort by score in descending order
        results = sorted(results, key=lambda x: x["score"], reverse=True)

        # Limit to top_k if specified
        if top_k and top_k > 0:
            results = results[:top_k]

        return results