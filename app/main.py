"""
Main module for the FastAPI application.

This module initializes the FastAPI application, sets up routes,
middlewares, error handlers, templates, and static files.
It also provides an entry point to run the app using Uvicorn.
"""

import os
import logging
from fastapi import FastAPI, APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from api.v1.routers import auth, documents, queries, files, pages
from app.config import settings
from app.api.middlewares import setup_middlewares
from utils.logger_util import get_logger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/api/redoc" if settings.ENVIRONMENT != "production" else None,
)

# Setup application middlewares
setup_middlewares(app)

# Setup router with versioned API prefix
api_router = APIRouter(prefix="/api")

# Register route modules
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(queries.router, prefix="/queries", tags=["Queries"])
api_router.include_router(files.router, prefix="/files", tags=["Files"])

# Include page routers - note these are protected by auth
app.include_router(pages.router, prefix="/pages", tags=["Pages"])
app.include_router(api_router)

# Serve static files from ./static directory if it exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info(f"Static files mounted from: {static_dir}")

# Jinja2 template configuration
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

@app.get("/", include_in_schema=False)
async def root():
    """
    Root endpoint redirecting to API documentation message.
    """
    return {"message": f"Welcome to {settings.APP_NAME}. Visit /api/docs for the API documentation."}


@app.get("/health", include_in_schema=False)
async def health_check():
    """
    Health check endpoint.
    """
    return {"status": "healthy", "version": settings.APP_VERSION}


# -------------------
# Custom Error Handlers
# -------------------

@app.exception_handler(403)
async def forbidden_exception_handler(request: Request, exc: HTTPException):
    """
    Handle 403 Forbidden error.
    """
    return templates.TemplateResponse("403.html", {"request": request}, status_code=403)


@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc: HTTPException):
    """
    Handle 404 Not Found error.
    """
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)


@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: HTTPException):
    """
    Handle 500 Internal Server error.
    """
    return templates.TemplateResponse("500.html", {"request": request}, status_code=500)


# -------------------
# Entry Point
# -------------------

def main():
    """
    Run the FastAPI app using Uvicorn.
    """
    logger.info(f"Starting {settings.APP_NAME}...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT != "production",
        workers=1,
        log_level="info"
    )

if __name__ == "__main__":
    main()
