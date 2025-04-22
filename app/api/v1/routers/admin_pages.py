# app/api/routes/admin_pages.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from api.v1.routers.auth import get_current_active_user
from app.infrastructure.database.db_models import User, File
from infrastructure.repositories import get_async_db

# Set up templates
templates = Jinja2Templates(directory="app/templates")

router = APIRouter()


# Middleware to check if user is admin
async def verify_admin(current_user: User = Depends(get_current_active_user)):
    """Verify if the current user is an admin."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
        request: Request,
        admin_user: User = Depends(verify_admin),
        db: Session = Depends(get_async_db)
):
    """
    Admin dashboard home.

    Parameters
    ----------
    request : Request
        The FastAPI request object
    admin_user : User
        The current admin user (verified)
    db : Session
        Database session

    Returns
    -------
    HTMLResponse
        Rendered admin dashboard template
    """
    # Get system stats for admin dashboard
    user_count = db.query(User).count()
    file_count = db.query(File).count()

    return templates.TemplateResponse(
        "admin/index.html",
        {
            "request": request,
            "user": admin_user,
            "user_count": user_count,
            "file_count": file_count,
            "page_title": "Admin Dashboard",
            "active_page": "admin_dashboard"
        }
    )


@router.get("/users", response_class=HTMLResponse)
async def admin_users(
        request: Request,
        admin_user: User = Depends(verify_admin),
        db: Session = Depends(get_async_db)
):
    """
    Admin user management page.

    Parameters
    ----------
    request : Request
        The FastAPI request object
    admin_user : User
        The current admin user (verified)
    db : Session
        Database session

    Returns
    -------
    HTMLResponse
        Rendered user management template
    """
    # Get all users in the system
    users = db.query(User).all()

    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "user": admin_user,
            "users": users,
            "page_title": "User Management",
            "active_page": "admin_users"
        }
    )


@router.get("/files", response_class=HTMLResponse)
async def admin_files(
        request: Request,
        admin_user: User = Depends(verify_admin),
        db: Session = Depends(get_async_db)
):
    """
    Admin file management page.

    Parameters
    ----------
    request : Request
        The FastAPI request object
    admin_user : User
        The current admin user (verified)
    db : Session
        Database session

    Returns
    -------
    HTMLResponse
        Rendered file management template
    """
    # Get all files in the system
    files = db.query(File).all()

    return templates.TemplateResponse(
        "admin/files.html",
        {
            "request": request,
            "user": admin_user,
            "files": files,
            "page_title": "File Management",
            "active_page": "admin_files"
        }
    )


@router.get("/settings", response_class=HTMLResponse)
async def admin_settings(
        request: Request,
        admin_user: User = Depends(verify_admin)
):
    """
    Admin system settings page.

    Parameters
    ----------
    request : Request
        The FastAPI request object
    admin_user : User
        The current admin user (verified)

    Returns
    -------
    HTMLResponse
        Rendered system settings template
    """
    return templates.TemplateResponse(
        "admin/settings.html",
        {
            "request": request,
            "user": admin_user,
            "page_title": "System Settings",
            "active_page": "admin_settings"
        }
    )


@router.get("/logs", response_class=HTMLResponse)
async def admin_logs(
        request: Request,
        admin_user: User = Depends(verify_admin)
):
    """
    Admin logs viewer page.

    Parameters
    ----------
    request : Request
        The FastAPI request object
    admin_user : User
        The current admin user (verified)

    Returns
    -------
    HTMLResponse
        Rendered logs viewer template
    """
    # Here you would implement logic to read system logs
    # For example purposes, we'll just create dummy data
    logs = [
        {"level": "INFO", "timestamp": "2025-04-08 10:00:00", "message": "System started"},
        {"level": "WARNING", "timestamp": "2025-04-08 10:05:23", "message": "High memory usage detected"},
        {"level": "ERROR", "timestamp": "2025-04-08 10:12:45", "message": "Failed login attempt from 192.168.1.1"}
    ]

    return templates.TemplateResponse(
        "admin/logs.html",
        {
            "request": request,
            "user": admin_user,
            "logs": logs,
            "page_title": "System Logs",
            "active_page": "admin_logs"
        }
    )