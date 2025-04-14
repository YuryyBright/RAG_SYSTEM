# app/api/routes/task_pages.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from api.middleware_auth import get_current_active_user
from app.infrastructure.database.db_models import User
from core.templates.templates import templates

router = APIRouter()


@router.get("/tasks", response_class=HTMLResponse)
async def tasks_page(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """
    Tasks management page.

    Parameters
    ----------
    request : Request
        The FastAPI request object
    current_user : User
        The current authenticated user from JWT token

    Returns
    -------
    HTMLResponse
        Rendered tasks page template
    """
    return templates.TemplateResponse(
        "/user/tasks.html",
        {
            "request": request,
            "username": current_user.username,
            "page_title": "Processing Tasks"
        }
    )