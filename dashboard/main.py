"""
FastAPI application for Device Dashboard.
"""
import os
import asyncio
import subprocess
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from dashboard.config import SESSION_COOKIE_NAME
from dashboard.auth.session import UserSession, session_store
from dashboard.auth.deps import get_current_session, require_session


def _get_git_hash() -> str:
    """Get the short git hash for cache-busting static assets."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return "dev"


_GIT_HASH = _get_git_hash()


class Templates:
    """Jinja2 template renderer with autoescape=False so script blocks
    and JS template literals are emitted as raw HTML."""

    def __init__(self, directory: str):
        from jinja2 import Environment, FileSystemLoader
        self._env = Environment(
            loader=FileSystemLoader(directory),
            autoescape=False,
        )

    def TemplateResponse(self, request: Request, name: str, context: dict) -> HTMLResponse:
        """Render a template. Signature matches Jinja2Templates for drop-in use."""
        tmpl = self._env.get_template(name)
        session = getattr(request.state, "session", None)
        context.setdefault("session", session)
        context.setdefault("request", request)
        body = tmpl.render(**context, git_hash=_GIT_HASH)
        return HTMLResponse(content=body, status_code=200, media_type="text/html")


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
    yield
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Device Dashboard",
    description="Web UI for managing postmarketOS on Redmi Note 7",
    version="1.0.0",
    lifespan=lifespan,
)

# Trust all hosts since we bind to 0.0.0.0
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Attach rate limiter to app state
from dashboard.api.auth import limiter as auth_limiter  # noqa: E402
app.state.limiter = auth_limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Middleware: no-cache on static files & session resolution on requests
@app.middleware("http")
async def _app_middleware(request: Request, call_next):
    # Resolve session from cookie and attach to request.state
    await get_current_session(request)

    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


# Templates — use autoescape=False so <script> blocks render as raw HTML
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Templates(templates_dir)


# Import route modules after app creation to avoid circular imports
from dashboard.api import auth, system, device, live  # noqa: E402

# Register API routers
app.include_router(auth.router)
app.include_router(system.router, prefix="/api")
app.include_router(device.router, prefix="/api")
app.include_router(live.router, prefix="/api")


# Login page route (public)
@app.get("/login", response_class=HTMLResponse, summary="Sign in page")
async def page_login(request: Request) -> HTMLResponse:
    session = getattr(request.state, "session", None)
    if session:
        next_url = request.query_params.get("next", "/")
        return RedirectResponse(url=next_url if next_url.startswith("/") else "/")
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"request": request},
    )


# Page routes — protected by require_session
PAGES: dict[str, tuple[str, str]] = {
    "/": ("index.html", "Landing page with overview"),
    "/services": ("services.html", "Systemd services"),
    "/processes": ("processes.html", "Running processes"),
    "/storage": ("storage.html", "Storage and disks"),
    "/network": ("network.html", "Network interfaces"),
    "/battery": ("battery.html", "Battery and device info"),
    "/packages": ("packages.html", "Package management"),
    "/users": ("users.html", "User management"),
    "/power": ("power.html", "Power controls"),
}


from typing import Optional


def _register_page(path: str, template_name: str, summary: str) -> None:
    if path == "/":
        # Homepage is public — accessible without authentication
        async def page(
            request: Request,
            session: Optional[UserSession] = Depends(get_current_session),
        ) -> HTMLResponse:
            return templates.TemplateResponse(
                request=request, name=template_name, context={"request": request, "session": session}
            )
    else:
        # All other pages require authentication
        async def page(
            request: Request,
            session: UserSession = Depends(require_session),
        ) -> HTMLResponse:
            return templates.TemplateResponse(
                request=request, name=template_name, context={"request": request, "session": session}
            )

    page.__name__ = f"page_{template_name.removesuffix('.html')}"
    app.get(path, response_class=HTMLResponse, summary=summary)(page)


for _path, (_template, _summary) in PAGES.items():
    _register_page(_path, _template, _summary)
