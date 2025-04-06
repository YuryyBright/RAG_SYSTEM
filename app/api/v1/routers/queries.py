# app/api/routes/queries.py
from fastapi import APIRouter, Depends
from api.schemas.query import QueryRequest, QueryResponse
from core.use_cases.query import QueryProcessor
from app.api.dependencies import get_query_processor

router = APIRouter()

@router.post("/", response_model=QueryResponse)
async def query_documents(
    query_request: QueryRequest,
    query_processor: QueryProcessor = Depends(get_query_processor)
):
    """
    Query documents and get an answer.

    Parameters
    ----------
    query_request : QueryRequest
        The query request data.
    query_processor : QueryProcessor
        The query processor dependency.

    Returns
    -------
    QueryResponse
        The query response containing the answer and sources.
    """
    result = await query_processor.process_query(
        query=query_request.query,
        top_k=query_request.top_k,
        rerank_top_k=query_request.rerank_top_k
    )

    return QueryResponse(
        answer=result["answer"],
        sources=result["sources"],
        has_answer=result["has_answer"]
    )