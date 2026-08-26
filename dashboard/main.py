"""
FastAPI application for Hermes Device Dashboard.
"""
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles


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
        body = tmpl.render(**context)
        return HTMLResponse(content=body, status_code=200, media_type="text/html")


app = FastAPI(
    title="RN7 Linux Dashboard",
    description="Web UI for managing postmarketOS on Redmi Note 7",
    version="1.0.0",
)

# Trust all hosts since we bind to 0.0.0.0
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Templates — use autoescape=False so <script> blocks render as raw HTML
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Templates(templates_dir)


# Import route modules after app creation to avoid circular imports
from dashboard.api import system, hermes, device, live  # noqa: E402

# Register API routers
app.include_router(system.router, prefix="/api")
app.include_router(hermes.router, prefix="/api")
app.include_router(device.router, prefix="/api")
app.include_router(live.router, prefix="/api")


# Page routes — every page is a static template render, so register them
# from a table instead of repeating ten identical handler bodies.
PAGES: dict[str, tuple[str, str]] = {
    "/": ("index.html", "Landing page with overview"),
    "/services": ("services.html", "Systemd services"),
    "/processes": ("processes.html", "Running processes"),
    "/storage": ("storage.html", "Storage and disks"),
    "/network": ("network.html", "Network interfaces"),
    "/battery": ("battery.html", "Battery and device info"),
    "/hermes": ("hermes.html", "Hermes AI integration"),
    "/packages": ("packages.html", "Package management"),
    "/users": ("users.html", "User management"),
    "/power": ("power.html", "Power controls"),
}


def _register_page(path: str, template_name: str, summary: str) -> None:
    async def page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request, name=template_name, context={"request": request}
        )

    page.__name__ = f"page_{template_name.removesuffix('.html')}"
    app.get(path, response_class=HTMLResponse, summary=summary)(page)


for _path, (_template, _summary) in PAGES.items():
    _register_page(_path, _template, _summary)

