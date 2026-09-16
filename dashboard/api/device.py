"""
API routes for device-level operations.
Protected with session authentication and privilege verification.
"""
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, Depends

from dashboard.auth.session import UserSession
from dashboard.auth.deps import require_session, require_admin, get_current_session
from dashboard.dependencies import run_command
from dashboard.auth.bridge import run_sudo_async
from dashboard.services.network import (
    get_ip_addresses,
    get_wifi_info,
    get_dns_servers,
    ping_test,
    get_gateways,
)
from dashboard.services.battery import (
    get_battery_info,
    get_thermal_zones,
    get_cpu_frequencies,
    get_cpu_scaling_available,
)
from dashboard.services.packages import (
    get_installed_count,
    get_upgradable_packages,
    upgrade_packages,
    search_packages,
)
from dashboard.services.users import (
    get_users,
    get_all_users,
    get_groups,
    get_current_user,
    get_sudoers_info,
)
from dashboard.services.power import (
    reboot,
    poweroff,
    suspend,
)

router = APIRouter()


# ---- Network ----

@router.get("/device/network")
async def api_network(session: UserSession = Depends(require_session)):
    """Get network information."""
    return {
        "interfaces": get_ip_addresses(),
        "wifi": get_wifi_info(),
        "dns": get_dns_servers(),
        "gateways": get_gateways(),
    }


@router.get("/device/network/ping")
async def api_ping(
    target: str = Query("8.8.8.8", description="Target to ping"),
    session: UserSession = Depends(require_session),
):
    """Ping a target and return results."""
    return ping_test(target)


# ---- Battery / Device Stats ----

@router.get("/device/battery")
async def api_battery(session: Optional[UserSession] = Depends(get_current_session)):
    """Get battery and device stats."""
    return {
        "battery": get_battery_info(),
        "thermal": get_thermal_zones(),
        "cpu_freq": get_cpu_frequencies(),
        "cpu_scaling": get_cpu_scaling_available(),
    }


# ---- Packages ----

@router.get("/device/packages")
async def api_packages(session: UserSession = Depends(require_session)):
    """Get package information."""
    return {
        "installed_count": get_installed_count(),
        "upgradable": get_upgradable_packages(),
    }


@router.post("/device/packages/upgrade")
async def api_upgrade_packages(session: UserSession = Depends(require_admin)):
    """Upgrade all packages (requires administrative privileges)."""
    code, out, err = await run_sudo_async(["apk", "upgrade"], password=None)
    if code != 0:
        raise HTTPException(status_code=500, detail=err or out or "Upgrade failed")
    return {"action": "upgrade", "success": True, "output": out}


@router.get("/device/packages/search")
async def api_search_packages(
    query: str = Query(..., min_length=1),
    session: UserSession = Depends(require_session),
):
    """Search for packages."""
    return {"results": search_packages(query)}


# ---- Users ----

@router.get("/device/users")
async def api_users(session: UserSession = Depends(require_session)):
    """Get user and group information."""
    return {
        "users": get_users(),
        "all_users": get_all_users(),
        "groups": get_groups(),
        "current_user": get_current_user(),
        "sudoers": get_sudoers_info(),
    }


# ---- Power Controls (Admin Gated) ----

@router.post("/device/power/reboot")
async def api_reboot(session: UserSession = Depends(require_admin)):
    """Reboot the system (requires administrative privileges)."""
    code, out, err = await run_sudo_async(["systemctl", "reboot"], password=None)
    if code != 0:
        raise HTTPException(status_code=500, detail=err or out or "Reboot failed")
    return {"action": "reboot", "success": True, "output": out}


@router.post("/device/power/poweroff")
async def api_poweroff(session: UserSession = Depends(require_admin)):
    """Power off the system (requires administrative privileges)."""
    code, out, err = await run_sudo_async(["systemctl", "poweroff"], password=None)
    if code != 0:
        raise HTTPException(status_code=500, detail=err or out or "Poweroff failed")
    return {"action": "poweroff", "success": True, "output": out}


@router.post("/device/power/suspend")
async def api_suspend(session: UserSession = Depends(require_admin)):
    """Suspend the system (requires administrative privileges)."""
    code, out, err = await run_sudo_async(["systemctl", "suspend"], password=None)
    if code != 0:
        raise HTTPException(status_code=500, detail=err or out or "Suspend failed")
    return {"action": "suspend", "success": True, "output": out}
