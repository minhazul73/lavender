"""
API routes for device-level operations.
Protected with session authentication and privilege verification.
"""
import asyncio
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, Depends

from dashboard.auth.session import UserSession
from dashboard.auth.deps import require_session, require_admin, get_current_session
from dashboard.dependencies import run_command
from dashboard.auth.bridge import run_sudo_async
from dashboard.services.network import (
    get_ip_addresses,
    get_wifi_info,
    get_dns_info,
    get_dns_servers,
    ping_test,
    get_gateways,
    get_network_summary,
    dns_lookup,
    scan_wifi_networks,
)
from dashboard.services.battery import (
    get_battery_info,
    get_thermal_zones,
    get_cpu_frequencies,
    get_cpu_scaling_available,
)
from dashboard.services.packages import (
    get_installed_count,
    get_installed_packages,
    get_upgradable_packages,
    upgrade_packages,
    search_packages,
    get_package_info,
    invalidate_packages_cache,
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
from dashboard.services.device_info import get_system_info

router = APIRouter()


# ---- System & Hardware Info ----

@router.get("/device/info")
async def api_device_info(session: Optional[UserSession] = Depends(get_current_session)):
    """Get dynamic system, hardware model, OS, and kernel metadata."""
    return get_system_info()


# ---- Network ----

@router.get("/device/network")
async def api_network(session: UserSession = Depends(require_session)):
    """Get complete network information."""
    dns_info = get_dns_info()
    return {
        "summary": get_network_summary(),
        "interfaces": get_ip_addresses(),
        "wifi": get_wifi_info(),
        "dns": dns_info.get("upstream_ips", []),
        "dns_details": dns_info,
        "gateways": get_gateways(),
    }


@router.get("/device/network/ping")
async def api_ping(
    target: str = Query("8.8.8.8", description="Target to ping"),
    count: int = Query(3, ge=1, le=10, description="Ping packet count"),
    session: UserSession = Depends(require_session),
):
    """Ping a target and return results."""
    return ping_test(target, count=count)


@router.get("/device/network/dns-query")
async def api_dns_query(
    domain: str = Query("google.com", description="Domain to resolve"),
    session: UserSession = Depends(require_session),
):
    """Test resolving a domain and measure latency."""
    return dns_lookup(domain)


@router.post("/device/network/wifi-scan")
async def api_wifi_scan(
    session: UserSession = Depends(require_session),
):
    """Trigger WiFi scan for nearby networks."""
    return {"networks": scan_wifi_networks()}


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
async def api_packages(
    refresh: bool = False,
    include_list: bool = True,
    session: UserSession = Depends(require_session),
):
    """Get package overview (installed count, upgradable list, full installed list)."""
    installed = await asyncio.to_thread(get_installed_packages, force_refresh=refresh) if include_list else []
    upgradable = await asyncio.to_thread(get_upgradable_packages)
    upgradable_list = [p for p in upgradable if not p.get("error")]
    return {
        "installed_count": len(installed) if include_list else await asyncio.to_thread(get_installed_count),
        "upgradable_count": len(upgradable_list),
        "upgradable": upgradable,
        "installed": installed,
    }


@router.post("/device/packages/upgrade")
async def api_upgrade_packages(
    package: Optional[str] = Query(None, description="Optional single package name to upgrade"),
    session: UserSession = Depends(require_admin),
):
    """Upgrade all packages or a single package (requires administrative privileges)."""
    cmd = ["apk", "add", "-u", package] if package else ["apk", "upgrade"]
    code, out, err = await run_sudo_async(cmd, password=None)
    invalidate_packages_cache()
    if code != 0:
        raise HTTPException(status_code=500, detail=err or out or "Upgrade failed")
    return {"action": "upgrade", "package": package, "success": True, "output": out}


@router.post("/device/packages/install")
async def api_install_package(
    package: str = Query(..., min_length=1, description="Package name to install"),
    session: UserSession = Depends(require_admin),
):
    """Install a package (requires administrative privileges)."""
    code, out, err = await run_sudo_async(["apk", "add", package], password=None)
    invalidate_packages_cache()
    if code != 0:
        raise HTTPException(status_code=500, detail=err or out or f"Failed to install {package}")
    return {"action": "install", "package": package, "success": True, "output": out}


@router.post("/device/packages/remove")
async def api_remove_package(
    package: str = Query(..., min_length=1, description="Package name to remove"),
    session: UserSession = Depends(require_admin),
):
    """Remove an installed package (requires administrative privileges)."""
    code, out, err = await run_sudo_async(["apk", "del", package], password=None)
    invalidate_packages_cache()
    if code != 0:
        raise HTTPException(status_code=500, detail=err or out or f"Failed to remove {package}")
    return {"action": "remove", "package": package, "success": True, "output": out}


@router.get("/device/packages/search")
async def api_search_packages(
    query: str = Query(..., min_length=1),
    session: UserSession = Depends(require_session),
):
    """Search for packages in repositories."""
    results = await asyncio.to_thread(search_packages, query)
    return {"results": results}


@router.get("/device/packages/info")
async def api_package_info(
    package: str = Query(..., min_length=1),
    session: UserSession = Depends(require_session),
):
    """Get package details."""
    info = await asyncio.to_thread(get_package_info, package)
    return info


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
