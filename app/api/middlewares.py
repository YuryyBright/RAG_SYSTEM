"""
This module defines custom middlewares for the FastAPI application.

Middlewares:
- AuthenticationMiddleware: Handles authentication for protected routes.
- LoggingMiddleware: Logs request and response information.
- ErrorHandlingMiddleware: Handles exceptions and returns appropriate responses.
- CORSMiddleware: Handles Cross-Origin Resource Sharing.
"""

from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Callable
import time
import uuid
from app.config import settings
from utils.logger_util import get_logger

logger = get_logger("app.api.middleware")


def setup_middlewares(app: FastAPI) -> None:
    """
    Setup all middlewares for the application.

    Parameters
    ----------
    app : FastAPI
        The FastAPI application instance.
    """
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Other middlewares can be added here
    app.middleware("http")(logging_middleware)
    app.middleware("http")(error_handling_middleware)



async def logging_middleware(request: Request, call_next: Callable) -> JSONResponse:
    """
    Middleware for logging request and response information.

    Parameters
    ----------
    request : Request
        The incoming request.
    call_next : Callable
        The next middleware or route handler.

    Returns
    -------
    JSONResponse
        The response from the next middleware or route handler.
    """
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    start_time = time.time()

    # Log request
    logger.info(f"Request started | ID: {request_id} | Method: {request.method} | Path: {request.url.path}")

    # Process request
    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # Log response
        logger.info(
            f"Request completed | ID: {request_id} | Method: {request.method} | "
            f"Path: {request.url.path} | Status: {response.status_code} | "
            f"Duration: {process_time:.3f}s"
        )

        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"Request failed | ID: {request_id} | Method: {request.method} | "
            f"Path: {request.url.path} | Duration: {process_time:.3f}s | Error: {str(e)}",
            exc_info=True
        )
        raise


async def error_handling_middleware(request: Request, call_next: Callable) -> JSONResponse:
    """
    Middleware for handling exceptions and returning appropriate responses.

    Parameters
    ----------
    request : Request
        The incoming request.
    call_next : Callable
        The next middleware or route handler.

    Returns
    -------
    JSONResponse
        The response from the next middleware or route handler, or an error response.
    """
    try:
        return await call_next(request)
    except Exception as e:
        # Handle different types of exceptions differently
        if hasattr(e, "status_code"):
            status_code = e.status_code
        else:
            status_code = 500

        return JSONResponse(
            status_code=status_code,
            content={
                "detail": str(e),
                "request_id": getattr(request.state, "request_id", None)
            }
        )