"""
Authentication API endpoints: Login, Logout, Elevation, and User Profile.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from server.auth.bridge import (
    AuthError,
    authenticate_user,
    drop_sudo_ticket,
    verify_sudo_password,
)
from server.auth.deps import get_current_session, require_session
from server.auth.session import UserSession, session_store
from server.core.config import (
    LOGIN_RATE_LIMIT,
    REQUIRE_AUTH_FOR_HOMEPAGE,
    SESSION_COOKIE_NAME,
    SESSION_MAX_IDLE_MINUTES,
)
from server.schemas.auth import ElevateRequest, LoginRequest

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/config", summary="Get public authentication and navigation configuration")
async def api_auth_config():
    """Return public authentication configuration (e.g. whether homepage requires auth)."""
    return {
        "require_auth_for_homepage": REQUIRE_AUTH_FOR_HOMEPAGE,
    }


SAFE_REDIRECT_ROUTES = {
    "/": "/",
    "/overview": "/overview",
    "/services": "/services",
    "/processes": "/processes",
    "/storage": "/storage",
    "/network": "/network",
    "/packages": "/packages",
    "/users": "/users",
    "/power": "/power",
}


def _sanitize_next_url(target: str | None) -> str:
    """Ensure redirect URL strictly matches a known internal application route."""
    if not target or not isinstance(target, str):
        return "/"
    target_clean = target.strip().split("?")[0].split("#")[0]
    return SAFE_REDIRECT_ROUTES.get(target_clean, "/")


@router.post("/login")
@limiter.limit(LOGIN_RATE_LIMIT)
async def api_login(
    payload: LoginRequest,
    request: Request,
):
    """
    Authenticate Linux user credentials against localhost SSH bridge.
    Accepts JSON payload validated by LoginRequest. Sets signed HttpOnly session cookie.
    """
    username = payload.username.strip()
    password = payload.password
    safe_next = _sanitize_next_url(payload.next)

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    # Offload PAM credential verification to thread pool via authenticate_user
    try:
        user_info = await authenticate_user(username, password)
    except AuthError as exc:
        logger.warning("Authentication failed for user %s: %s", username, exc)
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        ) from exc
    except Exception:
        logger.exception("Unexpected login error for %s", username)
        raise HTTPException(status_code=500, detail="Login system error")

    # Authentication succeeded: create session and set signed cookie
    session = await session_store.create(username, user_info)
    signed_token = session_store.sign_session_id(session.session_id)

    res = JSONResponse(content={
        "success": True,
        "username": username,
        "redirect": safe_next,
        "is_admin": session.is_elevated(),
        "can_elevate": session.can_elevate(),
    })

    client_host = request.client.host if request.client else ""
    is_secure = client_host not in ("127.0.0.1", "localhost", "::1")

    res.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=signed_token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_MAX_IDLE_MINUTES * 60,
        path="/",
        secure=is_secure,
    )
    return res


async def _do_logout(request: Request, session: UserSession | None):
    if session:
        await drop_sudo_ticket()
        await session_store.delete(session.session_id)

    is_json = request.headers.get("accept", "").startswith("application/json")
    if is_json and request.method == "POST":
        res = JSONResponse(content={"success": True})
    else:
        raw_next = request.query_params.get("next")
        if raw_next:
            next_url = _sanitize_next_url(raw_next)
        else:
            next_url = "/" if not REQUIRE_AUTH_FOR_HOMEPAGE else "/login?msg=Logged+out+successfully"
        res = RedirectResponse(url=next_url, status_code=status.HTTP_303_SEE_OTHER)

    res.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return res


@router.get("/logout", summary="Log out user via GET")
async def api_logout_get(
    request: Request,
    session: UserSession | None = Depends(get_current_session),
):
    return await _do_logout(request, session)


@router.post("/logout", summary="Log out user via POST")
async def api_logout_post(
    request: Request,
    session: UserSession | None = Depends(get_current_session),
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
        logger.warning("Administrative elevation failed for user %s", session.username)
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
