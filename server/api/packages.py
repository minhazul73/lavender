"""
Package Management API routes for Lavender.
Supports Alpine (apk), Debian/Ubuntu (apt), Arch (pacman), and Fedora (dnf).
"""
import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from server.auth.bridge import run_sudo_async
from server.auth.deps import require_admin, require_session
from server.auth.session import UserSession
from server.services.packages import (
    get_installed_count,
    get_installed_packages,
    get_package_info,
    get_package_manager,
    get_upgradable_packages,
    invalidate_packages_cache,
    search_packages,
)

router = APIRouter()


@router.get("", summary="Get package management overview")
@router.get("/", include_in_schema=False)
@router.get("/packages", include_in_schema=False)
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


@router.post("/upgrade", summary="Upgrade packages")
@router.post("/packages/upgrade", include_in_schema=False)
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


@router.post("/install", summary="Install package")
@router.post("/packages/install", include_in_schema=False)
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


@router.post("/remove", summary="Remove package")
@router.post("/packages/remove", include_in_schema=False)
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


@router.get("/search", summary="Search packages")
@router.get("/packages/search", include_in_schema=False)
async def api_search_packages(
    query: str = Query(..., min_length=1, description="Search query string"),
    session: UserSession = Depends(require_session),
):
    """Search for packages in repositories."""
    results = await asyncio.to_thread(search_packages, query)
    return {"results": results}


@router.get("/info", summary="Get package details")
@router.get("/packages/info", include_in_schema=False)
async def api_package_info(
    package: str = Query(..., min_length=1, description="Package name"),
    session: UserSession = Depends(require_session),
):
    """Get package details."""
    info = await asyncio.to_thread(get_package_info, package)
    return info
