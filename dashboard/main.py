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


@app.get("/")
async def index(request: Request):
    """Landing page with overview."""
    return templates.TemplateResponse(request=request, name="index.html", context={"request": request})


@app.get("/services")
async def services_page(request: Request):
    """Systemd services page."""
    return templates.TemplateResponse(request=request, name="services.html", context={"request": request})


@app.get("/processes")
async def processes_page(request: Request):
    """Processes page."""
    return templates.TemplateResponse(request=request, name="processes.html", context={"request": request})


@app.get("/storage")
async def storage_page(request: Request):
    """Storage/disk page."""
    return templates.TemplateResponse(request=request, name="storage.html", context={"request": request})


@app.get("/network")
async def network_page(request: Request):
    """Network page."""
    return templates.TemplateResponse(request=request, name="network.html", context={"request": request})


@app.get("/battery")
async def battery_page(request: Request):
    """Battery & device info page."""
    return templates.TemplateResponse(request=request, name="battery.html", context={"request": request})


@app.get("/hermes")
async def hermes_page(request: Request):
    """Hermes AI integration page."""
    return templates.TemplateResponse(request=request, name="hermes.html", context={"request": request})


@app.get("/packages")
async def packages_page(request: Request):
    """Package management page."""
    return templates.TemplateResponse(request=request, name="packages.html", context={"request": request})


@app.get("/users")
async def users_page(request: Request):
    """User management page."""
    return templates.TemplateResponse(request=request, name="users.html", context={"request": request})


@app.get("/power")
async def power_page(request: Request):
    """Power & network page."""
    return templates.TemplateResponse(request=request, name="power.html", context={"request": request})
