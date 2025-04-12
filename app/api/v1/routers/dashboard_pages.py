# app/api/routes/dashboard_pages.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware_auth import get_current_active_user
from app.infrastructure.database.db_models import User, File
from app.infrastructure.database.repository import get_async_db
from core.templates.templates import templates
from infrastructure.database.repository.file_repository import FileRepository

# Set up templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard_home(
        request: Request,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db)
):
    """
    Main dashboard home page after login.

    Parameters
    ----------
    request : Request
        The FastAPI request object
    current_user : User
        The current authenticated user
    db : Session
        Database session

    Returns
    -------
    HTMLResponse
        Rendered dashboard home template
    """

    files_manager = FileRepository(db)
    # Get counts for dashboard statistics
    file_count = await files_manager.get_by_owner(current_user.id)

    # You can add more statistics here as needed

    return templates.TemplateResponse(
        "/dashboard/index.html",
        {
            "request": request,
            "user": current_user,
            "file_count": len(file_count),
            "page_title": "Dashboard",
            "active_page": "dashboard"
        }
    )


@router.get("/files", response_class=HTMLResponse)
async def files_page(
        request: Request,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db)
):
    """
    Files management page.

    Parameters
    ----------
    request : Request
        The FastAPI request object
    current_user : User
        The current authenticated user
    db : Session
        Database session

    Returns
    -------
    HTMLResponse
        Rendered files management template
    """
    # Get user's files
    files = db.query(File).filter(File.owner_id == current_user.id).all()

    return templates.TemplateResponse(
        "dashboard/files.html",
        {
            "request": request,
            "user": current_user,
            "files": files,
            "page_title": "File Management",
            "active_page": "files"
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
        The current authenticated user

    Returns
    -------
    HTMLResponse
        Rendered documents management template
    """
    return templates.TemplateResponse(
        "dashboard/documents.html",
        {
            "request": request,
            "user": current_user,
            "page_title": "Document Management",
            "active_page": "documents"
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
        The current authenticated user

    Returns
    -------
    HTMLResponse
        Rendered settings template
    """
    return templates.TemplateResponse(
        "dashboard/settings.html",
        {
            "request": request,
            "user": current_user,
            "page_title": "Settings",
            "active_page": "settings"
        }
    )


@router.get("/upload", response_class=HTMLResponse)
async def upload_page(
        request: Request,
        current_user: User = Depends(get_current_active_user)
):
    """
    File upload page.

    Parameters
    ----------
    request : Request
        The FastAPI request object
    current_user : User
        The current authenticated user

    Returns
    -------
    HTMLResponse
        Rendered file upload template
    """
    return templates.TemplateResponse(
        "dashboard/upload.html",
        {
            "request": request,
            "user": current_user,
            "page_title": "Upload Files",
            "active_page": "upload"
        }
    )


@router.get("/shared", response_class=HTMLResponse)
async def shared_files_page(
        request: Request,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db)
):
    """
    Shared files page.

    Parameters
    ----------
    request : Request
        The FastAPI request object
    current_user : User
        The current authenticated user
    db : Session
        Database session

    Returns
    -------
    HTMLResponse
        Rendered shared files template
    """
    # Get public files owned by the user
    shared_files = db.query(File).filter(
        File.owner_id == current_user.id,
        File.is_public == True
    ).all()

    return templates.TemplateResponse(
        "dashboard/shared.html",
        {
            "request": request,
            "user": current_user,
            "shared_files": shared_files,
            "page_title": "Shared Files",
            "active_page": "shared"
        }
    )