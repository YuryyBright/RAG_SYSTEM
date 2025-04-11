# app/api/routes/auth_pages.py
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from starlette.status import HTTP_302_FOUND

from adapters.auth.service import AuthService
from api.v1.routers.auth import get_current_active_user
from app.infrastructure.database.repository import get_async_db
from utils.security import COOKIE_NAME

router = APIRouter()

from app.core.templates.templates import templates


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request,
                     db: AsyncSession = Depends(get_async_db)):
    """
    Login page.

    Parameters
    ----------
    request : Request
        The FastAPI request object

    Returns
    -------
    HTMLResponse
        Rendered login template
    """

    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "page_title": "Login"
            }
        )


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """
    Registration page.

    Parameters
    ----------
    request : Request
        The FastAPI request object

    Returns
    -------
    HTMLResponse
        Rendered registration template
    """
    return templates.TemplateResponse(
        "register.html",
        {
            "request": request,
            "page_title": "Register"
        }
    )


@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    """
    Forgot password page.

    Parameters
    ----------
    request : Request
        The FastAPI request object

    Returns
    -------
    HTMLResponse
        Rendered forgot password template
    """
    return templates.TemplateResponse(
        "forgot-password.html",
        {
            "request": request,
            "page_title": "Forgot Password"
        }
    )


@router.get("/reset-password/{token}", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: str):
    """
    Reset password page.

    Parameters
    ----------
    request : Request
        The FastAPI request object
    token : str
        Password reset token

    Returns
    -------
    HTMLResponse
        Rendered reset password template
    """
    return templates.TemplateResponse(
        "reset-password.html",
        {
            "request": request,
            "token": token,
            "page_title": "Reset Password"
        }
    )


# AJAX Routes for authentication
@router.get("/check-auth")
async def check_auth(request: Request):
    """
    Check if user is authenticated.

    This endpoint can be used by client-side JavaScript to verify
    if the user's session is still valid without reloading the page.

    Parameters
    ----------
    request : Request
        The FastAPI request object

    Returns
    -------
    dict
        Authentication status
    """
    try:
        user = await get_current_active_user(db=next(get_async_db()), token=request.cookies.get(COOKIE_NAME))
        return {"authenticated": True, "username": user.username}
    except:
        return {"authenticated": False}
