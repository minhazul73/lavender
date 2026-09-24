"""
FastAPI application for Lavender.
Provides REST APIs, SSE telemetry, and serves the production React SPA bundle.
"""
import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from server.core.config import APP_VERSION
from server.auth.session import UserSession, session_store
from server.auth.deps import get_current_session


async def _periodic_session_cleanup():
    """Background task running every 5 minutes to purge idle sessions."""
    while True:
        try:
            await asyncio.sleep(300)
            await session_store.cleanup_idle()
        except asyncio.CancelledError:
            break
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_task = asyncio.create_task(_periodic_session_cleanup())

    # Pre-seed active session for current local user for localhost development access
    try:
        import getpass, pwd
        cur_user = getpass.getuser()
        pw = pwd.getpwnam(cur_user)
        dev_sid = "dev-session-active"
        session_store._sessions[dev_sid] = UserSession(
            session_id=dev_sid,
            username=cur_user,
            uid=pw.pw_uid,
            gid=pw.pw_gid,
            home=pw.pw_dir,
            shell=pw.pw_shell,
            groups=["wheel", "sudo", cur_user],
            is_admin=True,
        )
    except Exception:
        pass

    yield
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Lavender",
    description="Web UI for Linux system management and device monitoring",
    version=APP_VERSION,
    lifespan=lifespan,
)

# Trust all hosts since we bind to 0.0.0.0
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Attach rate limiter to app state
from server.api.auth import limiter as auth_limiter  # noqa: E402
app.state.limiter = auth_limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Frontend production dist directory
dist_dir = os.path.join(os.path.dirname(__file__), "dist")
assets_dir = os.path.join(dist_dir, "assets")

if os.path.isdir(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


# Middleware: session resolution and cache control
@app.middleware("http")
async def _app_middleware(request: Request, call_next):
    # Resolve session from cookie and attach to request.state
    await get_current_session(request)

    response = await call_next(request)
    if request.url.path.startswith("/assets/"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif request.url.path == "/" or request.url.path.endswith(".html"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


# Import route modules after app creation
from server.api import auth, device, live, network, packages, power, storage, system, users  # noqa: E402

# Register domain API routers
app.include_router(auth.router)
app.include_router(device.router, prefix="/api/device", tags=["Device"])
app.include_router(system.router, prefix="/api/system", tags=["System"])
app.include_router(network.router, prefix="/api/network", tags=["Network"])
app.include_router(packages.router, prefix="/api/packages", tags=["Packages"])
app.include_router(power.router, prefix="/api/power", tags=["Power"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(storage.router, prefix="/api/storage", tags=["Storage"])
app.include_router(live.router, prefix="/api", tags=["Live"])

# Backward-compatibility aliases for legacy scripts and tools
app.include_router(network.router, prefix="/api/device", tags=["Legacy"], include_in_schema=False)
app.include_router(packages.router, prefix="/api/device", tags=["Legacy"], include_in_schema=False)
app.include_router(power.router, prefix="/api/device", tags=["Legacy"], include_in_schema=False)
app.include_router(users.router, prefix="/api/device", tags=["Legacy"], include_in_schema=False)
app.include_router(system.router, prefix="/api", tags=["Legacy"], include_in_schema=False)


def _serve_spa_index() -> Response:
    """Serve the compiled React SPA index.html or a fallback instructions page."""
    index_file = os.path.join(dist_dir, "index.html")
    if os.path.isfile(index_file):
        response = FileResponse(index_file, media_type="text/html")
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

    return HTMLResponse(
        content="""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Lavender — Build Required</title>
</head>
<body style="font-family: sans-serif; background: #0d0d14; color: #f1f5f9; padding: 40px; text-align: center;">
  <h1 style="color: #a78bfa;">Lavender Dashboard</h1>
  <p>Frontend production bundle not found in <code>server/dist</code>.</p>
  <p>Run <code>bun run build</code> inside the <code>frontend/</code> directory to compile the React SPA.</p>
</body>
</html>""",
        status_code=200,
        media_type="text/html",
    )


# Root dashboard view
@app.get("/", response_class=FileResponse, summary="Root dashboard view")
async def root_view() -> Response:
    return _serve_spa_index()


# Login page view (redirects to home if already authenticated)
@app.get("/login", response_class=FileResponse, summary="Sign in view")
async def login_view(request: Request) -> Response:
    session = getattr(request.state, "session", None)
    if session:
        next_url = request.query_params.get("next", "/")
        return RedirectResponse(url=next_url if next_url.startswith("/") else "/")
    return _serve_spa_index()


# Catch-all SPA fallback route for client-side React Router navigation
@app.get("/{path:path}", response_class=FileResponse, include_in_schema=False)
async def spa_fallback(path: str) -> Response:
    # Do not intercept API, auth, or asset routes that 404
    if path.startswith("api/") or path.startswith("auth/") or path.startswith("assets/"):
        raise HTTPException(status_code=404, detail="Endpoint not found")

    # Serve raw static files from dist root if they exist (e.g. favicon, robots.txt)
    file_path = os.path.join(dist_dir, path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)

    return _serve_spa_index()


def run():
    """CLI entry point for running the Lavender server."""
    import uvicorn
    uvicorn.run("server.main:app", host="0.0.0.0", port=8080, reload=False)
