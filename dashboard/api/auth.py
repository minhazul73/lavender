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

from dashboard.config import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_IDLE_MINUTES,
    LOGIN_RATE_LIMIT,
)
from dashboard.auth.session import UserSession, session_store
from dashboard.auth.bridge import (
    authenticate_user,
    verify_session_sudo,
    drop_session_sudo,
    AuthError,
    BridgeConnectionError,
)
from dashboard.auth.deps import get_current_session, require_session

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
        auth_mode, ssh_conn, user_info = await authenticate_user(username, password)
    except AuthError as exc:
        if is_json:
            raise HTTPException(status_code=401, detail=str(exc))
        return RedirectResponse(
            url=f"/login?error=Invalid+username+or+password&next={next}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except BridgeConnectionError as exc:
        if is_json:
            raise HTTPException(status_code=503, detail=str(exc))
        return RedirectResponse(
            url=f"/login?error=Authentication+service+unavailable&next={next}",
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
    session = await session_store.create(username, user_info, ssh_conn, auth_mode=auth_mode)
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
            "auth_mode": session.auth_mode,
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


@router.api_route("/logout", methods=["GET", "POST"])
async def api_logout(
    request: Request,
    session: Optional[UserSession] = Depends(get_current_session),
):
    """
    Log out user, drop sudo ticket, close SSH connection, and clear session cookie.
    """
    if session:
        await drop_session_sudo(session)
        await session_store.delete(session.session_id)

    is_json = request.headers.get("accept", "").startswith("application/json")
    if is_json and request.method == "POST":
        res = JSONResponse(content={"success": True})
    else:
        res = RedirectResponse(url="/login?msg=Logged+out+successfully", status_code=status.HTTP_303_SEE_OTHER)

    res.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return res


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
    Prompts for user's Linux password and refreshes sudo ticket (SSH or Local).
    """
    password = payload.password
    if not password:
        raise HTTPException(status_code=400, detail="Password is required")

    valid, err = await verify_session_sudo(session, password)
    if not valid:
        logger.warning("Administrative elevation failed for user %s: %s", session.username, err)
        raise HTTPException(
            status_code=400,
            detail=err or "Invalid password or user not authorized in sudoers",
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
    await drop_session_sudo(session)
    session.drop_elevation()
    logger.info("User %s dropped administrative access", session.username)
    return {"success": True, "is_admin": False}
