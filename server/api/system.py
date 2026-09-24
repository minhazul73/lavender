"""
API routes for system-related operations.
Protected with session authentication and privilege verification.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends

from dashboard.auth.session import UserSession
from dashboard.auth.deps import require_session, require_admin, get_current_session
from dashboard.dependencies import (
    run_command,
    parse_passwd_users,
    parse_groups,
)
from dashboard.auth.bridge import (
    run_user_service_async,
    run_sudo_async,
)
from dashboard.services.systemd import (
    list_services,
    get_service_status,
    get_service_logs,
    service_action,
    get_recent_logs,
)
from dashboard.services.processes import (
    get_top_processes,
    get_system_load,
    kill_process,
    get_memory_info,
    get_memory_human,
)
from dashboard.services.storage import get_disk_usage

router = APIRouter()


# ---- Systemd Services ----

@router.get("/system/services")
async def api_list_services(
    scope: str = Query(None, description="Filter by scope: user, system, or all"),
    session: Optional[UserSession] = Depends(get_current_session),
):
    """List systemd services for current user and system."""
    user_only = scope == "user"
    system_only = scope == "system"
    services = list_services(user_only=user_only, system_only=system_only)
    return {"services": services, "count": len(services)}


@router.get("/system/services/{service_name}")
async def api_service_status(
    service_name: str,
    user: bool = Query(False),
    session: UserSession = Depends(require_session),
):
    """Get detailed status for a service."""
    status = get_service_status(service_name, user=user)
    return status


@router.get("/system/services/{service_name}/logs")
async def api_service_logs(
    service_name: str,
    lines: int = Query(50, ge=1, le=200),
    user: bool = Query(False),
    session: UserSession = Depends(require_session),
):
    """Get recent logs for a service."""
    logs = get_service_logs(service_name, lines=lines, user=user)
    return {"logs": logs, "service": service_name}


@router.post("/system/services/{service_name}/{action}")
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

@router.get("/system/storage")
async def api_storage(session: Optional[UserSession] = Depends(get_current_session)):
    """Get disk usage information."""
    return {
        "disks": get_disk_usage(),
    }


# ---- Processes ----

@router.get("/system/processes")
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


@router.post("/system/processes/kill")
async def api_kill_process(
    pid: int = Query(..., ge=1, description="PID to kill"),
    session: UserSession = Depends(require_admin),
):
    """Kill a process by PID (requires administrative elevation)."""
    code, out, err = await run_sudo_async(["kill", "-9", str(pid)], password=None)
    if code != 0:
        raise HTTPException(status_code=500, detail=err or out or f"Failed to kill PID {pid}")
    return {"action": "kill", "pid": pid, "success": True, "output": out}


@router.get("/system/memory")
async def api_memory(session: Optional[UserSession] = Depends(get_current_session)):
    """Get detailed memory info."""
    return {
        "human": get_memory_human(),
        "raw": get_memory_info(),
    }


# ---- Recent System Logs ----

@router.get("/system/logs")
async def api_recent_logs(
    lines: int = Query(20, ge=1, le=200),
    session: Optional[UserSession] = Depends(get_current_session),
):
    """Get recent system journal logs."""
    logs = get_recent_logs(lines=lines)
    return {"logs": logs, "count": len(logs)}
