"""
API routes for system-related operations.
Protected with session authentication and privilege verification.
"""
import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends

from server.auth.session import UserSession
from server.auth.deps import require_session, require_admin, get_current_session
from server.dependencies import (
    run_command,
    parse_passwd_users,
    parse_groups,
)
from server.auth.bridge import (
    run_user_service_async,
    run_sudo_async,
)
from server.services.systemd import (
    list_services,
    get_service_status,
    get_service_logs,
    service_action,
    get_recent_logs,
)
from server.services.processes import (
    get_top_processes,
    get_system_load,
    kill_process,
    get_memory_info,
    get_memory_human,
)
from server.services.storage import get_disk_usage, unmount

router = APIRouter()


# ---- Systemd Services ----

@router.get("/services", summary="List systemd services")
@router.get("/system/services", include_in_schema=False)
async def api_list_services(
    scope: str = Query(None, description="Filter by scope: user, system, or all"),
    session: Optional[UserSession] = Depends(get_current_session),
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
    valid_actions = ["start", "stop", "restart", "enable", "disable"]
    if action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action: {action}")

    # System services require admin elevation
    if not user and not session.is_elevated():
        raise HTTPException(
            status_code=403,
            detail="Administrative privileges required to modify system services.",
        )

    if user:
        code, out, err = await run_user_service_async(
            session.uid, ["systemctl", "--user", action, service_name]
        )
    else:
        code, out, err = await run_sudo_async(
            ["systemctl", action, service_name], password=None
        )
    if code != 0:
        raise HTTPException(status_code=500, detail=err or out or f"Failed to {action} {service_name}")
    return {
        "success": True,
        "action": action,
        "service": service_name,
        "user": user,
        "output": out,
    }


# ---- Storage / Disk ----

@router.get("/storage", summary="Get storage usage")
@router.get("/system/storage", include_in_schema=False)
async def api_storage(session: Optional[UserSession] = Depends(get_current_session)):
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
    session: Optional[UserSession] = Depends(get_current_session),
):
    """Get processes and system resource stats."""
    return {
        "processes": get_top_processes(sort_by=sort_by, limit=limit),
        "load": get_system_load(),
        "memory": get_memory_human(),
    }


@router.post("/processes/kill", summary="Kill process by PID")
@router.post("/system/processes/kill", include_in_schema=False)
async def api_kill_process(
    pid: int = Query(..., ge=1, description="PID to kill"),
    session: UserSession = Depends(require_admin),
):
    """Kill a process by PID (requires administrative elevation)."""
    code, out, err = await run_sudo_async(["kill", "-9", str(pid)], password=None)
    if code != 0:
        raise HTTPException(status_code=500, detail=err or out or f"Failed to kill PID {pid}")
    return {"action": "kill", "pid": pid, "success": True, "output": out}


@router.get("/memory", summary="Get system memory info")
@router.get("/system/memory", include_in_schema=False)
async def api_memory(session: Optional[UserSession] = Depends(get_current_session)):
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
    session: Optional[UserSession] = Depends(get_current_session),
):
    """Get recent system journal logs."""
    logs = get_recent_logs(lines=lines)
    return {"logs": logs, "count": len(logs)}
