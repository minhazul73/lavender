"""
Power Management API routes for Lavender.
Provides system reboot, poweroff, suspend, CPU governor tuning, and timed power scheduling.
"""
import asyncio
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from server.auth.bridge import run_sudo_async
from server.auth.deps import get_current_session, require_admin
from server.auth.session import UserSession
from server.services.battery import get_cpu_scaling_available, set_cpu_governor
from server.services.power import (
    cancel_scheduled_action,
    get_scheduled_shutdown,
    schedule_power_action,
)

router = APIRouter()


@router.post("/reboot", summary="Reboot system")
@router.post("/power/reboot", include_in_schema=False)
async def api_reboot(session: UserSession = Depends(require_admin)):
    """Reboot the system (requires administrative privileges)."""
    code, out, err = await run_sudo_async(["systemctl", "reboot"], password=None)
    if code != 0:
        raise HTTPException(status_code=500, detail=err or out or "Reboot failed")
    return {"action": "reboot", "success": True, "output": out}


@router.post("/poweroff", summary="Power off system")
@router.post("/power/poweroff", include_in_schema=False)
async def api_poweroff(session: UserSession = Depends(require_admin)):
    """Power off the system (requires administrative privileges)."""
    code, out, err = await run_sudo_async(["systemctl", "poweroff"], password=None)
    if code != 0:
        raise HTTPException(status_code=500, detail=err or out or "Poweroff failed")
    return {"action": "poweroff", "success": True, "output": out}


@router.post("/suspend", summary="Suspend system")
@router.post("/power/suspend", include_in_schema=False)
async def api_suspend(session: UserSession = Depends(require_admin)):
    """Suspend the system (requires administrative privileges)."""
    code, out, err = await run_sudo_async(["systemctl", "suspend"], password=None)
    if code != 0:
        raise HTTPException(status_code=500, detail=err or out or "Suspend failed")
    return {"action": "suspend", "success": True, "output": out}


@router.post("/governor", summary="Set CPU governor")
@router.post("/power/governor", include_in_schema=False)
async def api_set_governor(
    governor: str = Query(..., min_length=1, description="Target CPU governor name"),
    session: UserSession = Depends(require_admin),
):
    """Set CPU frequency governor across all CPU cores (Admin gated)."""
    res = await asyncio.to_thread(set_cpu_governor, governor)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to set CPU governor"))
    return res


@router.get("/state", summary="Get CPU governor and scheduled power state")
@router.get("/power/state", include_in_schema=False)
async def api_power_state(session: Optional[UserSession] = Depends(get_current_session)):
    """Get active CPU power profile and pending scheduled power actions."""
    gov_file = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
    current_gov = "unknown"
    if os.path.isfile(gov_file):
        try:
            with open(gov_file, "r") as f:
                current_gov = f.read().strip()
        except Exception:
            pass

    scaling = get_cpu_scaling_available()
    scheduled = get_scheduled_shutdown()

    return {
        "active_governor": current_gov,
        "available_governors": scaling.get("governors", []),
        "scheduled": scheduled,
    }


@router.post("/schedule", summary="Schedule a reboot or poweroff")
@router.post("/power/schedule", include_in_schema=False)
async def api_schedule_power(
    payload: dict,
    session: UserSession = Depends(require_admin),
):
    """Schedule a timed reboot or shutdown (Admin gated)."""
    action = payload.get("action", "").lower().strip()
    if action not in ("reboot", "poweroff"):
        raise HTTPException(status_code=400, detail="Action must be 'reboot' or 'poweroff'")

    try:
        minutes = int(payload.get("minutes", 0))
        if minutes < 1 or minutes > 1440:
            raise ValueError()
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Minutes must be an integer between 1 and 1440")

    message = payload.get("message", "Scheduled from Lavender dashboard")
    res = await asyncio.to_thread(schedule_power_action, action, minutes, message)
    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error", "Failed to schedule action"))
    return res


@router.post("/cancel-scheduled", summary="Cancel pending scheduled power action")
@router.post("/power/cancel-scheduled", include_in_schema=False)
async def api_cancel_scheduled_power(session: UserSession = Depends(require_admin)):
    """Cancel any pending scheduled shutdown or reboot (Admin gated)."""
    res = await asyncio.to_thread(cancel_scheduled_action)
    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error", "Failed to cancel scheduled action"))
    return res
