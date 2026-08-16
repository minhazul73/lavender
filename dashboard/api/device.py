"""
API routes for device-level operations.
"""
from fastapi import APIRouter, Query, HTTPException

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
async def api_network():
    """Get network information."""
    return {
        "interfaces": get_ip_addresses(),
        "wifi": get_wifi_info(),
        "dns": get_dns_servers(),
        "gateways": get_gateways(),
    }


@router.get("/device/network/ping")
async def api_ping(target: str = Query("8.8.8.8", description="Target to ping")):
    """Ping a target and return results."""
    return ping_test(target)


# ---- Battery / Device Stats ----

@router.get("/device/battery")
async def api_battery():
    """Get battery and device stats."""
    return {
        "battery": get_battery_info(),
        "thermal": get_thermal_zones(),
        "cpu_freq": get_cpu_frequencies(),
        "cpu_scaling": get_cpu_scaling_available(),
    }


# ---- Packages ----

@router.get("/device/packages")
async def api_packages():
    """Get package information."""
    return {
        "installed_count": get_installed_count(),
        "upgradable": get_upgradable_packages(),
    }


@router.post("/device/packages/upgrade")
async def api_upgrade_packages():
    """Upgrade all packages (requires sudo)."""
    result = upgrade_packages()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Upgrade failed"))
    return result


@router.get("/device/packages/search")
async def api_search_packages(query: str = Query(..., min_length=1)):
    """Search for packages."""
    return {"results": search_packages(query)}


# ---- Users ----

@router.get("/device/users")
async def api_users():
    """Get user and group information."""
    return {
        "users": get_users(),
        "all_users": get_all_users(),
        "groups": get_groups(),
        "current_user": get_current_user(),
        "sudoers": get_sudoers_info(),
    }


# ---- Power ----

@router.post("/device/power/reboot")
async def api_reboot():
    """Reboot the system."""
    result = reboot()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Reboot failed"))
    return result


@router.post("/device/power/poweroff")
async def api_poweroff():
    """Power off the system."""
    result = poweroff()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Poweroff failed"))
    return result


@router.post("/device/power/suspend")
async def api_suspend():
    """Suspend the system."""
    result = suspend()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Suspend failed"))
    return result
