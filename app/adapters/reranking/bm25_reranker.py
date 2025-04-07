# app/adapters/reranking/bm25_reranker.py
from typing import List, Dict, Any
import re
import math
from collections import Counter
from core.interfaces.reranking import RerankerInterface


class BM25Reranker(RerankerInterface):
    """
    Implementation of BM25 algorithm for document reranking.

    This class uses the BM25 algorithm, a traditional information retrieval
    scoring function, to rerank documents based on term frequency and inverse
    document frequency.

    Attributes:
        k1 (float): Term frequency saturation parameter.
        b (float): Length normalization parameter.
        epsilon (float): Small value to prevent division by zero.
    """

    def __init__(
            self,
            k1: float = 1.5,
            b: float = 0.75,
            epsilon: float = 0.25
    ):
        """
        Initialize the BM25 reranker.

        Args:
            k1 (float): Term frequency saturation parameter.
            b (float): Length normalization parameter.
            epsilon (float): Small value to prevent division by zero.
        """
        self.k1 = k1
        self.b = b
        self.epsilon = epsilon

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words.

        Args:
            text (str): The text to tokenize.

        Returns:
            List[str]: A list of tokens (words).
        """
        # Convert to lowercase and split on non-alphanumeric characters
        return re.findall(r'\w+', text.lower())

    def _compute_bm25_score(
            self,
            query_tokens: List[str],
            doc_tokens: List[str],
            doc_lengths: List[int],
            avg_doc_length: float,
            idf: Dict[str, float]
    ) -> float:
        """
        Compute BM25 score for a document.

        Args:
            query_tokens (List[str]): Tokens in the query.
            doc_tokens (List[str]): Tokens in the document.
            doc_lengths (List[int]): Lengths of all documents.
            avg_doc_length (float): Average document length.
            idf (Dict[str, float]): Inverse document frequency for each query token.

        Returns:
            float: The BM25 score.
        """
        doc_length = len(doc_tokens)
        doc_term_freq = Counter(doc_tokens)
        score = 0.0

        for token in query_tokens:
            if token in doc_term_freq:
                tf = doc_term_freq[token]
                score += (
                        idf.get(token, 0) *
                        (tf * (self.k1 + 1)) /
                        (tf + self.k1 * (1 - self.b + self.b * doc_length / avg_doc_length))
                )

        return score

    async def rerank(
            self,
            query: str,
            documents: List[Dict[str, Any]],
            top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents based on relevance to the query using BM25.

        Args:
            query (str): The query string to evaluate the relevance of the documents.
            documents (List[Dict[str, Any]]): A list of dictionaries, each representing a document.
            top_k (int): The number of top relevant documents to return.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing the top-k most relevant documents.
        """
        if not documents:
            return []

        # Tokenize query
        query_tokens = self._tokenize(query)

        if not query_tokens:
            return documents[:top_k]

        # Tokenize documents
        doc_contents = [doc.get("content", "") for doc in documents]
        doc_tokens = [self._tokenize(content) for content in doc_contents]

        # Calculate document lengths and average document length
        doc_lengths = [len(tokens) for tokens in doc_tokens]
        avg_doc_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 0

        # Calculate IDF (Inverse Document Frequency)
        idf = {}
        num_docs = len(doc_tokens)
        for token in query_tokens:
            doc_freq = sum(1 for tokens in doc_tokens if token in tokens)
            idf[token] = math.log((num_docs - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0)

        # Calculate BM25 scores
        scores = [
            self._compute_bm25_score(query_tokens, tokens, doc_lengths, avg_doc_length, idf)
            for tokens in doc_tokens
        ]

        # Normalize scores to [0, 1] range
        max_score = max(scores) if scores else 1.0
        normalized_scores = [score / (max_score + self.epsilon) for score in scores]

        # Create list of documents with scores
        scored_documents = []
        for i, doc in enumerate(documents):
            scored_doc = doc.copy()
            scored_doc["score"] = normalized_scores[i]
            scored_documents.append(scored_doc)

        # Sort by score in descending order
        scored_documents.sort(key=lambda x: x.get("score", 0), reverse=True)

        # Return top_k documents
        return scored_documents[:top_k]