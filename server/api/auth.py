"""
Authentication API endpoints: Login, Logout, Elevation, and User Profile.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Request, Response, Depends, HTTPException, Form, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from server.core.config import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_IDLE_MINUTES,
    LOGIN_RATE_LIMIT,
)
from server.auth.session import UserSession, session_store
from server.auth.bridge import (
    authenticate_user,
    verify_sudo_password,
    drop_sudo_ticket,
    AuthError,
)
from server.auth.deps import get_current_session, require_session

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str
    next: Optional[str] = "/"


class ElevateRequest(BaseModel):
    password: str


@router.post("/login")
@limiter.limit(LOGIN_RATE_LIMIT)
async def api_login(
    request: Request,
    response: Response,
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    next: Optional[str] = Form("/"),
):
    """
    Authenticate Linux user credentials against localhost SSH bridge.
    Accepts Form or JSON payloads. Sets signed HttpOnly session cookie.
    """
    is_json = request.headers.get("content-type", "").startswith("application/json")
    if is_json:
        try:
            body = await request.json()
            username = body.get("username", "").strip()
            password = body.get("password", "")
            next = body.get("next", "/")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
    else:
        username = (username or "").strip()
        password = password or ""
        next = next or "/"

    if not username or not password:
        err_msg = "Username and password are required"
        if is_json:
            raise HTTPException(status_code=400, detail=err_msg)
        return RedirectResponse(
            url=f"/login?error={err_msg}&next={next}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    try:
        user_info = await authenticate_user(username, password)
    except AuthError as exc:
        if is_json:
            raise HTTPException(status_code=401, detail=str(exc))
        return RedirectResponse(
            url=f"/login?error=Invalid+username+or+password&next={next}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception as exc:
        logger.exception("Unexpected login error for %s", username)
        if is_json:
            raise HTTPException(status_code=500, detail="Login system error")
        return RedirectResponse(
            url=f"/login?error=System+error&next={next}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Authentication succeeded: create session and set signed cookie
    session = await session_store.create(username, user_info)
    signed_token = session_store.sign_session_id(session.session_id)

    # Sanitize next parameter to prevent open redirects
    safe_next = next if next and next.startswith("/") and not next.startswith("//") else "/"

    if is_json:
        res = JSONResponse(content={
            "success": True,
            "username": username,
            "redirect": safe_next,
            "is_admin": session.is_admin,
            "can_elevate": session.can_elevate(),
        })
    else:
        res = RedirectResponse(url=safe_next, status_code=status.HTTP_303_SEE_OTHER)

    res.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=signed_token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_MAX_IDLE_MINUTES * 60,
        path="/",
    )
    return res


async def _do_logout(request: Request, session: Optional[UserSession]):
    if session:
        await drop_sudo_ticket()
        await session_store.delete(session.session_id)

    is_json = request.headers.get("accept", "").startswith("application/json")
    if is_json and request.method == "POST":
        res = JSONResponse(content={"success": True})
    else:
        res = RedirectResponse(url="/login?msg=Logged+out+successfully", status_code=status.HTTP_303_SEE_OTHER)

    res.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return res


@router.get("/logout", summary="Log out user via GET")
async def api_logout_get(
    request: Request,
    session: Optional[UserSession] = Depends(get_current_session),
):
    return await _do_logout(request, session)


@router.post("/logout", summary="Log out user via POST")
async def api_logout_post(
    request: Request,
    session: Optional[UserSession] = Depends(get_current_session),
):
    return await _do_logout(request, session)


@router.get("/me")
async def api_me(session: UserSession = Depends(require_session)):
    """Return active user profile and privilege status."""
    return session.to_dict()


@router.post("/elevate")
async def api_elevate(
    payload: ElevateRequest,
    session: UserSession = Depends(require_session),
):
    """
    Cockpit-style administrative elevation.
    Prompts for user's Linux password and refreshes sudo ticket locally.
    """
    password = payload.password
    if not password:
        raise HTTPException(status_code=400, detail="Password is required")

    valid, err = await verify_sudo_password(password)
    if not valid:
        logger.warning("Administrative elevation failed for user %s: %s", session.username, err)
        raise HTTPException(
            status_code=400,
            detail=f"Incorrect password for '{session.username}'. Please enter the password for user '{session.username}' (user must have wheel/sudo group permissions).",
        )

    session.elevate()
    logger.info("User %s elevated to administrative access (session %s)", session.username, session.session_id[:8])
    return {
        "success": True,
        "is_admin": True,
        "expires_in": session.admin_remaining_seconds(),
    }


@router.post("/drop-admin")
async def api_drop_admin(session: UserSession = Depends(require_session)):
    """Drop active administrative elevation and revoke sudo ticket."""
    await drop_sudo_ticket()
    session.drop_elevation()
    logger.info("User %s dropped administrative access", session.username)
    return {"success": True, "is_admin": False}
