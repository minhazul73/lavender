"""
API routes for Hermes-related operations.
"""
from fastapi import APIRouter

from dashboard.hermes.gateway import (
    get_gateway_status,
    get_dashboard_status,
    restart_gateway,
    restart_dashboard,
    get_gateway_logs,
    get_dashboard_logs,
    get_hermes_info,
    get_hermes_sessions_summary,
    get_cron_jobs,
    get_memory_pressure,
    get_network_quality,
)

router = APIRouter()


@router.get("/hermes/status")
async def api_hermes_status():
    """Get Hermes gateway and dashboard status."""
    return {
        "gateway": get_gateway_status(),
        "dashboard": get_dashboard_status(),
        "info": get_hermes_info(),
    }


@router.post("/hermes/restart-gateway")
async def api_restart_gateway():
    """Restart the Hermes gateway service."""
    result = restart_gateway()
    if not result["success"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=result.get("error", "Restart failed"))
    return result


@router.post("/hermes/restart-dashboard")
async def api_restart_dashboard():
    """Restart the Hermes dashboard service."""
    result = restart_dashboard()
    if not result["success"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=result.get("error", "Restart failed"))
    return result


@router.get("/hermes/logs")
async def api_hermes_logs(service: str = "gateway", lines: int = 50):
    """Get logs for Hermes services."""
    if service == "gateway":
        return {"logs": get_gateway_logs(lines), "service": "hermes-gateway"}
    elif service == "dashboard":
        return {"logs": get_dashboard_logs(lines), "service": "hermes-dashboard"}
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Unknown service: {service}")


@router.get("/hermes/cron")
async def api_hermes_cron():
    """Get Hermes cron job information."""
    return {"jobs": get_cron_jobs()}


@router.get("/hermes/sessions")
async def api_hermes_sessions():
    """Get Hermes sessions summary."""
    return {"sessions": get_hermes_sessions_summary()}


@router.get("/hermes/memory-pressure")
async def api_memory_pressure():
    """Check memory pressure status."""
    return get_memory_pressure()


@router.get("/hermes/network-quality")
async def api_network_quality():
    """Check network quality."""
    return get_network_quality()
