# app/adapters/reranking/cross_encoder.py
from typing import List, Dict, Any
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from core.interfaces.reranking import RerankerInterface


class CrossEncoderReranker(RerankerInterface):
    """
    Implementation of a cross-encoder model for document reranking.

    This class uses a pre-trained cross-encoder model to rerank documents based on
    their relevance to a given query.

    Attributes:
        model_name (str): The name/path of the cross-encoder model to use.
        tokenizer: The tokenizer for the cross-encoder model.
        model: The pre-trained cross-encoder model.
        device (str): The device to run the model on ('cpu' or 'cuda').
        max_length (int): The maximum sequence length for the model.
    """

    def __init__(
            self,
            model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
            max_length: int = 512,
            device: str = None
    ):
        """
        Initialize the cross-encoder reranker.

        Args:
            model_name (str): The name/path of the cross-encoder model to use.
            max_length (int): The maximum sequence length for the model.
            device (str): The device to run the model on. If None, will use CUDA if available.
        """
        self.model_name = model_name
        self.max_length = max_length

        # Determine device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        # Load tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.to(self.device)

    async def rerank(
            self,
            query: str,
            documents: List[Dict[str, Any]],
            top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents based on relevance to the query.

        Args:
            query (str): The query string to evaluate the relevance of the documents.
            documents (List[Dict[str, Any]]): A list of dictionaries, each representing a document.
            top_k (int): The number of top relevant documents to return.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing the top-k most relevant documents.
        """
        if not documents:
            return []

        # Extract document contents
        doc_contents = [doc.get("content", "") for doc in documents]

        # Create query-document pairs
        pairs = [[query, doc] for doc in doc_contents]

        # Tokenize pairs
        features = self.tokenizer(
            pairs,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt"
        ).to(self.device)

        # Get model predictions
        with torch.no_grad():
            scores = self.model(**features).logits.flatten()

        # Convert scores to CPU if necessary and to list
        scores = scores.cpu().tolist() if self.device == "cuda" else scores.tolist()

        # Create list of documents with scores
        scored_documents = []
        for i, doc in enumerate(documents):
            scored_doc = doc.copy()
            scored_doc["score"] = scores[i]
            scored_documents.append(scored_doc)

        # Sort by score in descending order
        scored_documents.sort(key=lambda x: x.get("score", 0), reverse=True)

        # Return top_k documents
        return scored_documents[:top_k]