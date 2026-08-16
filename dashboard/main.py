"""
FastAPI application for Hermes Device Dashboard.
"""
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from dashboard.config import PORT, HOST, DEBUG


def render_template(request: Request, template_name: str, context: dict) -> HTMLResponse:
    """Render a Jinja2 template with the given context."""
    templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
    return templates.TemplateResponse(template_name, context)

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

# Templates
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)


# Import route modules after app creation to avoid circular imports
from dashboard.api import system, hermes, device  # noqa: E402

# Register API routers
app.include_router(system.router, prefix="/api")
app.include_router(hermes.router, prefix="/api")
app.include_router(device.router, prefix="/api")


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
    """Battery/device stats page."""
    return templates.TemplateResponse(request=request, name="battery.html", context={"request": request})


@app.get("/hermes")
async def hermes_page(request: Request):
    """Hermes gateway/dashboard controls."""
    return templates.TemplateResponse(request=request, name="hermes.html", context={"request": request})


@app.get("/packages")
async def packages_page(request: Request):
    """Packages/updates page."""
    return templates.TemplateResponse(request=request, name="packages.html", context={"request": request})


@app.get("/users")
async def users_page(request: Request):
    """Users/permissions page."""
    return templates.TemplateResponse(request=request, name="users.html", context={"request": request})


@app.get("/power")
async def power_page(request: Request):
    """Power control page."""
    return templates.TemplateResponse(request=request, name="power.html", context={"request": request})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, log_level="info" if not DEBUG else "debug")
