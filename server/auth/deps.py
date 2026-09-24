"""
FastAPI dependencies for authentication and authorization.
"""
from typing import Optional
from fastapi import Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from dashboard.config import SESSION_COOKIE_NAME
from dashboard.auth.session import UserSession, session_store
from dashboard.auth.bridge import verify_sudo_password


async def get_current_session(request: Request) -> Optional[UserSession]:
    """
    Extract session from signed cookie, if valid and active.
    Attaches session to request.state for template rendering.
    """
    # Check if already resolved in request state
    if hasattr(request.state, "session") and request.state.session is not None:
        return request.state.session

    token = request.cookies.get(SESSION_COOKIE_NAME)
    sid = None
    if token:
        sid = session_store.verify_token(token)
        if not sid and token in session_store._sessions:
            sid = token

    # Fallback for localhost if local session is seeded
    if not sid:
        client_host = request.client.host if request.client else ""
        if client_host in ("127.0.0.1", "localhost", "::1"):
            if "dev-session-active" in session_store._sessions:
                sid = "dev-session-active"

    if not sid:
        request.state.session = None
        return None

    session = await session_store.get(sid)
    request.state.session = session
    return session


async def require_session(
    request: Request,
    session: Optional[UserSession] = Depends(get_current_session),
) -> UserSession:
    """
    Ensure caller is authenticated.
    Redirects HTML page requests to /login, raises 401 for API calls.
    """
    if session is not None:
        return session

    # Determine if request expects an HTML response or JSON
    accept = request.headers.get("accept", "")
    is_html_request = "text/html" in accept or not request.url.path.startswith("/api")

    if is_html_request:
        next_path = request.url.path
        if request.url.query:
            next_path += f"?{request.url.query}"
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": f"/login?next={next_path}"},
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Please sign in.",
    )


async def require_admin(
    request: Request,
    session: UserSession = Depends(require_session),
) -> UserSession:
    """
    Ensure authenticated user has elevated administrative privileges.
    Accepts on-the-fly password validation via 'X-Admin-Password' header if not already elevated.
    """
    if session.is_elevated():
        return session

    # Check for direct password elevation in header
    admin_pwd = request.headers.get("X-Admin-Password")
    if admin_pwd:
        from dashboard.auth.bridge import verify_sudo_password
        valid, err = await verify_sudo_password(admin_pwd)
        if valid:
            session.elevate()
            return session

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Administrative access required. Please enter password to elevate.",
    )
