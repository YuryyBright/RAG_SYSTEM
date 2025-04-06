from typing import Dict, Any, List
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    """
    Schema for query request.

    Attributes
    ----------
    query : str
        The user's question.
    top_k : int
        The number of documents to retrieve.
    rerank_top_k : int
        The number of documents after reranking.
    """
    query: str = Field(..., description="User question")
    top_k: int = Field(5, description="Number of documents to retrieve")
    rerank_top_k: int = Field(3, description="Number of documents after reranking")

class SourceInfo(BaseModel):
    """
    Information about a document source.

    Attributes
    ----------
    id : str
        The unique identifier of the document.
    metadata : Dict[str, Any]
        The metadata associated with the document.
    score : float
        The relevance score of the document.
    """
    id: str = Field(..., description="Document ID")
    metadata: Dict[str, Any] = Field(..., description="Document metadata")
    score: float = Field(..., description="Relevance score")

class QueryResponse(BaseModel):
    """
    Schema for query response.

    Attributes
    ----------
    answer : str
        The answer to the query.
    sources : List[SourceInfo]
        The source documents used to generate the answer.
    has_answer : bool
        Indicates whether an answer was found.
    """
    answer: str = Field(..., description="Answer to the query")
    sources: List[SourceInfo] = Field(default_factory=list, description="Source documents")
    has_answer: bool = Field(..., description="Whether an answer was found")