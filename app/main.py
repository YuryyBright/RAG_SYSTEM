"""
Main module for the FastAPI application.

This module initializes the FastAPI application, sets up routes,
middlewares, error handlers, templates, and static files.
It also provides an entry point to run the app using Uvicorn.
"""

import os
from fastapi import FastAPI, APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse
from starlette.status import HTTP_302_FOUND


from api.v1.routers import auth, documents, files, pages, auth_pages, dashboard_pages, admin_pages, user_api, \
    theme, task_pages, tasks, conversations
from api.websockets.task_updates import handle_task_websocket

from app.config import settings
from app.api.middlewares import setup_middlewares
from application.services.auth_service import AuthService
from infrastructure.repositories import get_async_db
from utils.logger_util import get_logger
from utils.security import COOKIE_NAME

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
api_router.include_router(files.router, prefix="/files", tags=["Files"])

api_router.include_router(conversations.router, prefix="/conversations", tags=["Conversations"])
# Include page routers - note these are protected by auth
app.include_router(pages.router, prefix="/pages", tags=["Pages"])

# Include page routers for frontend pages
app.include_router(auth_pages.router, prefix="/auth", tags=["Authentication Pages"])
app.include_router(dashboard_pages.router, prefix="/dashboard", tags=["Dashboard Pages"])
app.include_router(admin_pages.router, prefix="/admin", tags=["Admin Pages"])
api_router.include_router(user_api.router, prefix="/user", tags=["User"])
api_router.include_router(theme.router, prefix="/themes", tags=["Themes"])

api_router.include_router(tasks.router,prefix="/tasks",tags=["Tasks"])
# Add page routes
api_router.include_router(task_pages.router,prefix="")

# Add WebSocket endpoint
api_router.add_websocket_route("/ws/tasks", handle_task_websocket)
app.include_router(api_router)

# Serve static files from ./static directory if it exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info(f"Static files mounted from: {static_dir}")

# Jinja2 template configuration
from app.core.templates.templates import templates

# Root route - redirect to dashboard if logged in, otherwise to login page
@app.get("/", response_class=HTMLResponse)
async def root(request: Request, db: AsyncSession = Depends(get_async_db)):
    """Redirect to dashboard if logged in, else to login"""
    session_id = request.cookies.get(COOKIE_NAME)
    if not session_id:
        return RedirectResponse(url="/auth/login", status_code=HTTP_302_FOUND)

    try:
        auth_service = AuthService(db)
        user = await auth_service.get_user_by_session_id(session_id)
        if user and user.is_active:
            return RedirectResponse(url="/dashboard", status_code=HTTP_302_FOUND)
        else:
            return RedirectResponse(url="/auth/login", status_code=HTTP_302_FOUND)
    except Exception as e:
        logger.error(f"Error in root redirect: {e}")
        return RedirectResponse(url="/auth/login", status_code=HTTP_302_FOUND)

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
