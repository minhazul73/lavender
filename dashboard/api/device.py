"""
API routes for device-level operations.
Protected with session authentication and privilege verification.
"""
import asyncio
import os
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
    get_package_manager,
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
    get_human_users,
    get_system_users,
    get_categorized_groups,
    get_active_sessions,
    get_login_history,
    get_security_posture,
    get_user_ssh_keys,
    add_user_ssh_key,
    delete_user_ssh_key,
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
    mgr = get_package_manager()
    installed = await asyncio.to_thread(get_installed_packages, force_refresh=refresh) if include_list else []
    upgradable = await asyncio.to_thread(get_upgradable_packages)
    upgradable_list = [p for p in upgradable if not p.get("error")]
    return {
        "backend": mgr.id,
        "backend_name": mgr.name,
        "backend_short": mgr.short_name,
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
    mgr = get_package_manager()
    cmd = mgr.get_upgrade_command(package)
    if not cmd:
        raise HTTPException(status_code=400, detail="No upgrade command available for this system")
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
    mgr = get_package_manager()
    cmd = mgr.get_install_command(package)
    if not cmd:
        raise HTTPException(status_code=400, detail="No install command available for this system")
    code, out, err = await run_sudo_async(cmd, password=None)
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
    mgr = get_package_manager()
    cmd = mgr.get_remove_command(package)
    if not cmd:
        raise HTTPException(status_code=400, detail="No remove command available for this distribution")
    code, out, err = await run_sudo_async(cmd, password=None)
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


# ---- Users & Sessions ----

@router.get("/device/users")
async def api_users(session: UserSession = Depends(require_session)):
    """Get user, session, group, and access control information."""
    username = session.username if session else None
    human_users = await asyncio.to_thread(get_human_users, username)
    system_users = await asyncio.to_thread(get_system_users)
    categorized_groups = await asyncio.to_thread(get_categorized_groups)
    active_sessions = await asyncio.to_thread(get_active_sessions)
    login_history = await asyncio.to_thread(get_login_history, 10)
    security_posture = await asyncio.to_thread(get_security_posture)
    current_user_info = await asyncio.to_thread(get_current_user)
    sudoers_info = await asyncio.to_thread(get_sudoers_info)

    active_sessions_count = len(active_sessions)
    human_users_count = len(human_users)
    total_ssh_keys = sum(u.get("ssh_keys_count", 0) for u in human_users)
    is_elevated = session.is_elevated() if session else False

    return {
        "human_users": human_users,
        "system_users": system_users,
        "groups_categorized": categorized_groups,
        "active_sessions": active_sessions,
        "login_history": login_history,
        "security": security_posture,
        "metrics": {
            "active_sessions_count": active_sessions_count,
            "human_users_count": human_users_count,
            "total_ssh_keys": total_ssh_keys,
            "is_elevated": is_elevated,
        },
        # Backwards compatibility
        "users": human_users,
        "all_users": system_users,
        "groups": categorized_groups,
        "current_user": current_user_info,
        "sudoers": sudoers_info,
    }


@router.post("/device/users/session/terminate")
async def api_terminate_session(
    payload: dict,
    session: UserSession = Depends(require_admin),
):
    """Terminate an active terminal or SSH session (Admin gated)."""
    tty = payload.get("tty", "").strip()
    if not tty:
        raise HTTPException(status_code=400, detail="Missing TTY name")
    clean_tty = os.path.basename(tty)
    code, out, err = await run_sudo_async(["pkill", "-9", "-t", clean_tty])
    if code != 0 and "No such process" in (out + err):
        await run_sudo_async(["loginctl", "terminate-session", clean_tty])
    return {"success": True, "message": f"Session on {clean_tty} terminated"}


@router.get("/device/users/{username}/ssh-keys")
async def api_get_ssh_keys(
    username: str,
    session: UserSession = Depends(require_session),
):
    """Get installed public SSH keys for a user."""
    if session.username != username and not session.is_elevated():
        raise HTTPException(status_code=403, detail="Admin privileges required to view other users' keys")
    keys = await asyncio.to_thread(get_user_ssh_keys, username)
    return {"username": username, "keys": keys}


@router.post("/device/users/{username}/ssh-keys")
async def api_add_ssh_key(
    username: str,
    payload: dict,
    session: UserSession = Depends(require_session),
):
    """Add a public SSH key to a user's authorized_keys."""
    if session.username != username and not session.is_elevated():
        raise HTTPException(status_code=403, detail="Admin privileges required to modify other users' keys")
    key = payload.get("key", "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="Key content is required")
    success = await asyncio.to_thread(add_user_ssh_key, username, key)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid public key format or failed to write")
    return {"success": True, "message": "SSH key added successfully"}


@router.delete("/device/users/{username}/ssh-keys/{key_index}")
async def api_delete_ssh_key(
    username: str,
    key_index: int,
    session: UserSession = Depends(require_session),
):
    """Delete a public SSH key by index."""
    if session.username != username and not session.is_elevated():
        raise HTTPException(status_code=403, detail="Admin privileges required to modify other users' keys")
    success = await asyncio.to_thread(delete_user_ssh_key, username, key_index)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete key")
    return {"success": True, "message": "SSH key removed"}


@router.post("/device/users/{username}/groups")
async def api_update_user_groups(
    username: str,
    payload: dict,
    session: UserSession = Depends(require_admin),
):
    """Update secondary groups for a user (Admin gated)."""
    groups = payload.get("groups", [])
    if not isinstance(groups, list):
        raise HTTPException(status_code=400, detail="Groups must be a list of group names")
    groups_arg = ",".join(groups)
    code, out, err = await run_sudo_async(["usermod", "-G", groups_arg, username])
    if code != 0:
        raise HTTPException(status_code=500, detail=f"Failed to update groups: {err or out}")
    return {"success": True, "message": f"Updated groups for {username}"}


@router.post("/device/users/{username}/password")
async def api_change_password(
    username: str,
    payload: dict,
    session: UserSession = Depends(require_session),
):
    """Change user password (Self or Admin gated)."""
    if session.username != username and not session.is_elevated():
        raise HTTPException(status_code=403, detail="Admin privileges required")
    new_pass = payload.get("new_password", "").strip()
    if not new_pass or len(new_pass) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")

    # Update password via chpasswd using run_sudo_async with password
    # On Linux: echo 'username:new_pass' | sudo chpasswd
    try:
        proc = await asyncio.create_subprocess_exec(
            "sudo", "-n", "chpasswd",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=f"{username}:{new_pass}\n".encode()),
            timeout=10,
        )
        if proc.returncode != 0:
            err = stderr.decode().strip() or stdout.decode().strip()
            raise HTTPException(status_code=500, detail=f"Failed to change password: {err}")
        return {"success": True, "message": f"Password successfully updated for {username}"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Password update error: {str(e)}")


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
