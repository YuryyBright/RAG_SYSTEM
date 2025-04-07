"""
Main module for the FastAPI application.

This module initializes the FastAPI application, sets up routes,
middlewares, and other components necessary for the application.
"""

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
import os

from api.v1.routers import auth, documents, queries, files
from app.config import settings
from app.api.middlewares import setup_middlewares


# Initialize the FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/api/redoc" if settings.ENVIRONMENT != "production" else None,
)

# Setup middlewares
setup_middlewares(app)

# Create API router
api_router = APIRouter(prefix="/api")

# Include routes
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(queries.router, prefix="/queries", tags=["Queries"])
api_router.include_router(files.router, prefix="/files", tags=["Files"])

# Include the API router in the app
app.include_router(api_router)

# Mount static files if they exist
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Setup templates
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

@app.get("/", include_in_schema=False)
async def root():
    """
    Root endpoint redirecting to the API documentation.
    """
    return {"message": f"Welcome to {settings.APP_NAME}. Visit /api/docs for the API documentation."}

@app.get("/health", include_in_schema=False)
async def health_check():
    """
    Health check endpoint.
    """
    return {"status": "healthy", "version": settings.APP_VERSION}

# Custom error handlers

@app.exception_handler(403)
async def forbidden_exception_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse("403.html", {"request": request}, status_code=403)


@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)


@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse("500.html", {"request": request}, status_code=500)