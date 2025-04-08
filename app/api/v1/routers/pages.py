# app/api/routes/pages.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
from typing import Dict, Any

from api.middleware_auth import get_current_active_user
from app.infrastructure.database.db_models import User


# Set up templates
templates = Jinja2Templates(directory="app/templates")

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home_page(
        request: Request,
        current_user: User = Depends(get_current_active_user)
):
    """
    Home page after user login.

    Parameters
    ----------
    request : Request
        The FastAPI request object
    current_user : User
        The current authenticated user from JWT token

    Returns
    -------
    HTMLResponse
        Rendered home page template
    """
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "username": current_user.username,
            "page_title": "Home"
        }
    )


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
        request: Request,
        current_user: User = Depends(get_current_active_user)
):
    """
    User dashboard page.

    Parameters
    ----------
    request : Request
        The FastAPI request object
    current_user : User
        The current authenticated user from JWT token

    Returns
    -------
    HTMLResponse
        Rendered dashboard template
    """
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "username": current_user.username,
            "user_id": current_user.id,
            "email": current_user.email,
            "page_title": "Dashboard"
        }
    )


@router.get("/documents", response_class=HTMLResponse)
async def documents_page(
        request: Request,
        current_user: User = Depends(get_current_active_user)
):
    """
    Documents management page.

    Parameters
    ----------
    request : Request
        The FastAPI request object
    current_user : User
        The current authenticated user from JWT token

    Returns
    -------
    HTMLResponse
        Rendered documents page template
    """
    return templates.TemplateResponse(
        "documents.html",
        {
            "request": request,
            "username": current_user.username,
            "page_title": "Documents"
        }
    )


@router.get("/files", response_class=HTMLResponse)
async def files_page(
        request: Request,
        current_user: User = Depends(get_current_active_user)
):
    """
    Files management page.

    Parameters
    ----------
    request : Request
        The FastAPI request object
    current_user : User
        The current authenticated user from JWT token

    Returns
    -------
    HTMLResponse
        Rendered files page template
    """
    return templates.TemplateResponse(
        "files.html",
        {
            "request": request,
            "username": current_user.username,
            "page_title": "Files"
        }
    )


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
        request: Request,
        current_user: User = Depends(get_current_active_user)
):
    """
    User profile page.

    Parameters
    ----------
    request : Request
        The FastAPI request object
    current_user : User
        The current authenticated user from JWT token

    Returns
    -------
    HTMLResponse
        Rendered profile page template
    """
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "username": current_user.username,
            "email": current_user.email,
            "is_active": current_user.is_active,
            "page_title": "Profile"
        }
    )


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
        request: Request,
        current_user: User = Depends(get_current_active_user)
):
    """
    User settings page.

    Parameters
    ----------
    request : Request
        The FastAPI request object
    current_user : User
        The current authenticated user from JWT token

    Returns
    -------
    HTMLResponse
        Rendered settings page template
    """
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "username": current_user.username,
            "page_title": "Settings"
        }
    )


# For admin users
@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(
        request: Request,
        current_user: User = Depends(get_current_active_user)
):
    """
    Admin user management page.

    Parameters
    ----------
    request : Request
        The FastAPI request object
    current_user : User
        The current authenticated user from JWT token

    Returns
    -------
    HTMLResponse
        Rendered admin users page template

    Raises
    ------
    HTTPException
        If the user is not an admin
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "username": current_user.username,
            "page_title": "User Management"
        }
    )