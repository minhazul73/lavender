"""
API routes for system-related operations.
Protected with session authentication and privilege verification.
"""
import asyncio
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from server.auth.bridge import run_sudo_async, run_user_service_async
from server.auth.deps import get_current_session, require_admin, require_session
from server.auth.session import UserSession
from server.services.processes import (
    get_memory_human,
    get_memory_info,
    get_system_load,
    get_top_processes,
)
from server.services.storage import get_disk_usage, unmount
from server.services.systemd import (
    get_recent_logs,
    get_service_logs,
    get_service_status,
    list_services,
)

router = APIRouter()

SERVICE_NAME_REGEX = re.compile(r"^[a-zA-Z0-9_@.][a-zA-Z0-9_\-@.]*$")


def validate_service_name(name: str) -> str:
    """Validate systemd service/unit name to prevent argument injection."""
    if not name or len(name) > 256 or not SERVICE_NAME_REGEX.match(name):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid service name format: {name!r}",
        )
    return name


# ---- Systemd Services ----

@router.get("/services", summary="List systemd services")
@router.get("/system/services", include_in_schema=False)
async def api_list_services(
    scope: str = Query(None, description="Filter by scope: user, system, or all"),
    session: UserSession | None = Depends(get_current_session),
):
    """List systemd services for current user and system."""
    user_only = scope == "user"
    system_only = scope == "system"
    services = list_services(user_only=user_only, system_only=system_only)
    return {"services": services, "count": len(services)}


@router.get("/services/{service_name}", summary="Get service status")
@router.get("/system/services/{service_name}", include_in_schema=False)
async def api_service_status(
    service_name: str,
    user: bool = Query(False),
    session: UserSession = Depends(require_session),
):
    """Get detailed status for a service."""
    validate_service_name(service_name)
    status = get_service_status(service_name, user=user)
    return status


@router.get("/services/{service_name}/logs", summary="Get service logs")
@router.get("/system/services/{service_name}/logs", include_in_schema=False)
async def api_service_logs(
    service_name: str,
    lines: int = Query(50, ge=1, le=200),
    user: bool = Query(False),
    session: UserSession = Depends(require_session),
):
    """Get recent logs for a service."""
    validate_service_name(service_name)
    logs = get_service_logs(service_name, lines=lines, user=user)
    return {"logs": logs, "service": service_name}


@router.post("/services/{service_name}/{action}", summary="Execute action on service")
@router.post("/system/services/{service_name}/{action}", include_in_schema=False)
async def api_service_action(
    service_name: str,
    action: str,
    user: bool = Query(False),
    session: UserSession = Depends(require_session),
):
    """
    Start, stop, restart, enable, or disable a service.
    User services run under authenticated user's session.
    System services require administrative elevation.
    """
    validate_service_name(service_name)
    if action not in ("start", "stop", "restart", "enable", "disable"):
        raise HTTPException(status_code=400, detail=f"Invalid action: {action}")

    # System services require admin elevation
    if not user and not session.is_elevated():
        raise HTTPException(status_code=403, detail="Administrative privileges required to modify system services.")

    if user:
        code, out, err = await run_user_service_async(session.uid, ["systemctl", "--user", action, service_name])
    else:
        code, out, err = await run_sudo_async(["systemctl", action, service_name], password=None)
    if code != 0:
        raise HTTPException(status_code=500, detail=err or out or f"Failed to {action} {service_name}")
    return {"success": True, "action": action, "service": service_name, "user": user, "output": out}


class ServiceActionPayload(BaseModel):
    """Payload for executing a lifecycle action on a systemd service."""
    service: str
    action: str
    user: bool = False


@router.post("/services/action", summary="Execute action on service via body")
@router.post("/system/services/action", include_in_schema=False)
async def api_service_action_body(
    payload: ServiceActionPayload,
    session: UserSession = Depends(require_session),
):
    """Execute lifecycle action on systemd service using request body parameters."""
    return await api_service_action(
        service_name=payload.service,
        action=payload.action,
        user=payload.user,
        session=session,
    )


# ---- Storage / Disk ----

@router.get("/storage", summary="Get storage usage")
@router.get("/system/storage", include_in_schema=False)
async def api_storage(session: UserSession | None = Depends(get_current_session)):
    """Get disk usage information."""
    return {
        "disks": get_disk_usage(),
    }


@router.post("/storage/unmount", summary="Unmount disk")
@router.post("/system/storage/unmount", include_in_schema=False)
async def api_unmount(
    mount_point: str = Query(..., description="Mount point to unmount"),
    session: UserSession = Depends(require_admin),
):
    """Unmount a filesystem (requires administrative privileges)."""
    res = await asyncio.to_thread(unmount, mount_point)
    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error", "Unmount failed"))
    return res


# ---- Processes ----

@router.get("/processes", summary="Get processes and load stats")
@router.get("/system/processes", include_in_schema=False)
async def api_processes(
    sort_by: str = Query("mem", pattern="^(cpu|mem|pid|user|name)$"),
    limit: int = Query(0, ge=0, le=2000, description="0 returns all processes"),
    session: UserSession | None = Depends(get_current_session),
):
    """Get processes and system resource stats."""
    return {
        "processes": get_top_processes(sort_by=sort_by, limit=limit),
        "load": get_system_load(),
        "memory": get_memory_human(),
    }


class KillProcessRequest(BaseModel):
    """Request payload for terminating a process by PID."""
    pid: int = Field(..., ge=1, description="PID to kill")


@router.post("/processes/kill", summary="Kill process by PID")
@router.post("/system/processes/kill", include_in_schema=False)
async def api_kill_process(
    payload: KillProcessRequest | None = None,
    # Typed as Any to bypass eager FastAPI 422 validation and preserve 400 contract for invalid query PIDs
    pid: Any = Query(None, description="PID to kill (deprecated, use request body)"),
    session: UserSession = Depends(require_admin),
):
    """Kill a process by PID (requires administrative elevation).

    Accepts target PID in JSON request body (KillProcessRequest) or deprecated query parameter.
    If both are supplied, the body PID takes precedence.
    """
    if payload is not None:
        target_pid = payload.pid
    else:
        try:
            target_pid = int(pid) if pid is not None else None
            if target_pid is None or target_pid < 1:
                raise ValueError
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="PID must be a positive integer")

    code, out, err = await run_sudo_async(["kill", "-9", str(target_pid)], password=None)
    if code != 0:
        raise HTTPException(status_code=500, detail=err or out or f"Failed to kill PID {target_pid}")
    return {"action": "kill", "pid": target_pid, "success": True, "output": out}


@router.get("/memory", summary="Get system memory info")
@router.get("/system/memory", include_in_schema=False)
async def api_memory(session: UserSession | None = Depends(get_current_session)):
    """Get detailed memory info."""
    return {
        "human": get_memory_human(),
        "raw": get_memory_info(),
    }


# ---- Recent System Logs ----

@router.get("/logs", summary="Get recent journal logs")
@router.get("/system/logs", include_in_schema=False)
async def api_recent_logs(
    lines: int = Query(20, ge=1, le=200),
    limit: int | None = Query(None, ge=1, le=200),
    service: str | None = Query(None),
    session: UserSession | None = Depends(get_current_session),
):
    """Get recent system journal logs."""
    effective_lines = limit if limit is not None else lines
    if service:
        service_logs = get_service_logs(service, lines=effective_lines)
        log_lines = service_logs.strip().split("\n") if service_logs else []
        return {"logs": log_lines, "count": len(log_lines), "service": service}
    logs = get_recent_logs(lines=effective_lines)
    return {"logs": logs, "count": len(logs)}
