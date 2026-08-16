"""
API routes for system-related operations.
"""
from fastapi import APIRouter, HTTPException, Query
from dashboard.services.systemd import (
    list_services,
    get_service_status,
    get_service_logs,
    service_action,
    service_toggle_enabled,
    get_all_units,
)
from dashboard.services.storage import (
    get_disk_usage,
    get_mounts,
    get_dir_usage,
    unmount,
)
from dashboard.services.processes import (
    get_top_processes,
    get_system_load,
    kill_process,
    get_memory_info,
    get_memory_human,
)

router = APIRouter()


# ---- Systemd Services ----

@router.get("/system/services")
async def api_list_services(
    scope: str = Query(None, description="Filter by scope: user, system, or all"),
):
    """List systemd services."""
    user_only = scope == "user"
    system_only = scope == "system"
    services = list_services(user_only=user_only, system_only=system_only)
    return {"services": services, "count": len(services)}


@router.get("/system/services/{service_name}")
async def api_service_status(service_name: str, user: bool = Query(False)):
    """Get detailed status for a service."""
    status = get_service_status(service_name, user=user)
    return status


@router.get("/system/services/{service_name}/logs")
async def api_service_logs(
    service_name: str,
    lines: int = Query(50, ge=1, le=200),
    user: bool = Query(False),
):
    """Get recent logs for a service."""
    logs = get_service_logs(service_name, lines=lines, user=user)
    return {"logs": logs, "service": service_name}


@router.post("/system/services/{service_name}/{action}")
async def api_service_action(
    service_name: str,
    action: str,
    user: bool = Query(False),
):
    """Start, stop, restart, enable, or disable a service."""
    valid_actions = ["start", "stop", "restart", "enable", "disable"]
    if action not in valid_actions:
        # Handle toggle_enabled separately
        if action == "toggle_enabled":
            return {"error": "Use enable/disable directly"}
        raise HTTPException(status_code=400, detail=f"Invalid action: {action}")
    
    result = service_action(service_name, action, user=user)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Action failed"))
    return result


# ---- Storage / Disk ----

@router.get("/system/storage")
async def api_storage():
    """Get disk usage information."""
    return {
        "disks": get_disk_usage(),
        "mounts": get_mounts(),
        "dir_usage": get_dir_usage(),
    }


@router.post("/system/storage/unmount")
async def api_unmount(mount_point: str = Query(..., description="Mount point to unmount")):
    """Unmount a filesystem."""
    result = unmount(mount_point)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Unmount failed"))
    return result


# ---- Processes ----

@router.get("/system/processes")
async def api_processes(sort_by: str = Query("mem", pattern="^(cpu|mem)$"), limit: int = Query(20, ge=5, le=100)):
    """Get top processes."""
    return {
        "processes": get_top_processes(sort_by=sort_by, limit=limit),
        "load": get_system_load(),
        "memory": get_memory_human(),
    }


@router.post("/system/processes/kill")
async def api_kill_process(pid: int = Query(..., ge=1, description="PID to kill")):
    """Kill a process by PID."""
    result = kill_process(pid)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Kill failed"))
    return result


@router.get("/system/memory")
async def api_memory():
    """Get detailed memory info."""
    return {
        "human": get_memory_human(),
        "raw": get_memory_info(),
    }
