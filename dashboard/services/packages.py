"""
Package management using apk (Alpine Package Keeper).
"""
import re
import time
from typing import Optional

from dashboard.dependencies import run_command, run_sudo_command

# In-memory cache for installed packages list (reduces CPU/disk load on mobile device)
_PACKAGES_CACHE: dict = {
    "installed": None,
    "timestamp": 0.0,
    "ttl": 60.0,  # 60 seconds TTL
}


def invalidate_packages_cache():
    """Clear package cache so subsequent calls re-query the system."""
    _PACKAGES_CACHE["installed"] = None
    _PACKAGES_CACHE["timestamp"] = 0.0


def get_installed_packages(force_refresh: bool = False) -> list[dict]:
    """
    Get full list of installed packages with names and versions.
    Cached for 60 seconds to avoid repeating subprocess calls on phone.
    """
    now = time.time()
    if not force_refresh and _PACKAGES_CACHE["installed"] is not None:
        if (now - _PACKAGES_CACHE["timestamp"]) < _PACKAGES_CACHE["ttl"]:
            return _PACKAGES_CACHE["installed"]

    # apk info -v outputs: <name>-<version>-r<rel> e.g. 'busybox-1.36.1-r7'
    code, out, err = run_command(["apk", "info", "-v"], timeout=20)
    if code != 0:
        # Fallback to plain apk info
        code, out, err = run_command(["apk", "info"], timeout=15)
        if code != 0:
            return []

    packages = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        
        parts = line.rsplit("-", 2)
        if len(parts) == 3 and parts[1] and parts[2]:
            pkg = {
                "name": parts[0],
                "version": f"{parts[1]}-{parts[2]}",
                "full": line,
            }
        elif len(parts) == 2:
            pkg = {
                "name": parts[0],
                "version": parts[1],
                "full": line,
            }
        else:
            pkg = {
                "name": line,
                "version": "",
                "full": line,
            }
        packages.append(pkg)

    packages.sort(key=lambda p: p["name"].lower())
    _PACKAGES_CACHE["installed"] = packages
    _PACKAGES_CACHE["timestamp"] = now
    return packages


def get_installed_count() -> int:
    """Get count of installed packages."""
    if _PACKAGES_CACHE["installed"] is not None:
        return len(_PACKAGES_CACHE["installed"])
    code, out, err = run_command(["apk", "info"], timeout=15)
    if code == 0:
        lines = [line for line in out.splitlines() if line.strip()]
        return len(lines)
    return 0


def get_upgradable_packages() -> list[dict]:
    """
    Get list of packages that can be upgraded.
    """
    code, out, err = run_command(["apk", "list", "--upgradable"], timeout=20)
    if code != 0:
        return [{"error": err or "Failed to check upgradable packages"}]
    
    packages = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        # Format: package-version-arch {installed} (reasons) [upgradable from: old-version]
        parts = line.split()
        if len(parts) >= 1:
            pkg_info = {
                "full": line,
                "name": parts[0],
            }
            # Extract version
            if "-" in parts[0]:
                name_ver = parts[0].rsplit("-", 2)
                if len(name_ver) == 3:
                    pkg_info["name_clean"] = name_ver[0]
                    pkg_info["version"] = f"{name_ver[1]}-{name_ver[2]}"
                    pkg_info["arch"] = name_ver[2]
                else:
                    pkg_info["name_clean"] = parts[0]
            else:
                pkg_info["name_clean"] = parts[0]
            
            # Check for upgradable from
            if "[upgradable from:" in line:
                m = re.search(r"\[upgradable from:\s*([^\]]+)\]", line)
                if m:
                    pkg_info["current_version"] = m.group(1).strip()
            
            packages.append(pkg_info)
    
    return packages


def upgrade_packages() -> dict:
    """
    Run apk upgrade (requires sudo).
    """
    invalidate_packages_cache()
    code, out, err = run_sudo_command(["apk", "upgrade"], timeout=300)
    return {
        "success": code == 0,
        "output": out,
        "error": err,
    }


def upgrade_single_package(package_name: str) -> dict:
    """
    Upgrade a single package (requires sudo).
    """
    invalidate_packages_cache()
    code, out, err = run_sudo_command(["apk", "add", "-u", package_name], timeout=180)
    return {
        "success": code == 0,
        "output": out,
        "error": err,
    }


def install_package(package_name: str) -> dict:
    """
    Install a new package from repositories (requires sudo).
    """
    invalidate_packages_cache()
    code, out, err = run_sudo_command(["apk", "add", package_name], timeout=180)
    return {
        "success": code == 0,
        "output": out,
        "error": err,
    }


def remove_package(package_name: str) -> dict:
    """
    Remove an installed package (requires sudo).
    """
    invalidate_packages_cache()
    code, out, err = run_sudo_command(["apk", "del", package_name], timeout=120)
    return {
        "success": code == 0,
        "output": out,
        "error": err,
    }


def search_packages(query: str) -> list[dict]:
    """Search for packages by name in repositories."""
    query = query.strip()
    if not query:
        return []
    code, out, err = run_command(["apk", "search", query], timeout=15)
    if code != 0:
        return [{"error": err or "Package search failed"}]
    
    results = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.rsplit("-", 2)
        if len(parts) == 3 and parts[1] and parts[2]:
            name = parts[0]
            version = f"{parts[1]}-{parts[2]}"
        else:
            name = line
            version = ""
        results.append({"name": name, "version": version, "full": line})
    return results


def get_package_info(package_name: str) -> dict:
    """Get detailed info about an installed package."""
    code, out, err = run_command(["apk", "info", package_name], timeout=10)
    if code != 0:
        return {"error": err, "package": package_name}
    return {
        "package": package_name,
        "info": out,
    }
