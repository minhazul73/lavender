"""
Distro-Agnostic Package Management Service.
Supports Alpine/postmarketOS (apk), Debian/Ubuntu/Linux Mint (apt/dpkg),
Arch Linux/Manjaro (pacman), and Fedora/RHEL (dnf/rpm).
"""
import os
import re
import time
import shutil
from typing import Optional, List, Dict, Any

from dashboard.dependencies import run_command, run_sudo_command

# In-memory cache for installed packages list (reduces CPU/disk load on host)
_PACKAGES_CACHE: dict = {
    "installed": None,
    "timestamp": 0.0,
    "ttl": 60.0,  # 60 seconds TTL
}


def invalidate_packages_cache():
    """Clear package cache so subsequent calls re-query the system."""
    _PACKAGES_CACHE["installed"] = None
    _PACKAGES_CACHE["timestamp"] = 0.0


class BasePackageManager:
    """Abstract base class for distribution package manager adapters."""
    id: str = "generic"
    name: str = "Generic Package Manager"
    short_name: str = "Package Manager"

    def is_available(self) -> bool:
        return False

    def get_installed_packages(self) -> List[Dict[str, Any]]:
        return []

    def get_installed_count(self) -> int:
        return len(self.get_installed_packages())

    def get_upgradable_packages(self) -> List[Dict[str, Any]]:
        return []

    def search_packages(self, query: str) -> List[Dict[str, Any]]:
        return []

    def get_package_info(self, package_name: str) -> Dict[str, Any]:
        return {"package": package_name, "info": "Information not available"}

    def get_upgrade_command(self, package: Optional[str] = None) -> List[str]:
        return []

    def get_install_command(self, package: str) -> List[str]:
        return []

    def get_remove_command(self, package: str) -> List[str]:
        return []


class ApkManager(BasePackageManager):
    """Alpine Linux & postmarketOS Package Manager (apk)."""
    id = "apk"
    name = "Alpine Package Keeper (apk)"
    short_name = "apk"

    def is_available(self) -> bool:
        return bool(shutil.which("apk"))

    def get_installed_packages(self) -> List[Dict[str, Any]]:
        code, out, err = run_command(["apk", "info", "-v"], timeout=20)
        if code != 0:
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
        return packages

    def get_installed_count(self) -> int:
        code, out, err = run_command(["apk", "info"], timeout=15)
        if code == 0:
            lines = [l for l in out.splitlines() if l.strip()]
            return len(lines)
        return 0

    def get_upgradable_packages(self) -> List[Dict[str, Any]]:
        code, out, err = run_command(["apk", "list", "--upgradable"], timeout=20)
        if code != 0:
            return [{"error": err or "Failed to check upgradable packages"}]

        packages = []
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 1:
                pkg_info = {
                    "full": line,
                    "name": parts[0],
                }
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

                if "[upgradable from:" in line:
                    m = re.search(r"\[upgradable from:\s*([^\]]+)\]", line)
                    if m:
                        pkg_info["current_version"] = m.group(1).strip()

                packages.append(pkg_info)
        return packages

    def search_packages(self, query: str) -> List[Dict[str, Any]]:
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

    def get_package_info(self, package_name: str) -> Dict[str, Any]:
        code, out, err = run_command(["apk", "info", package_name], timeout=10)
        return {
            "package": package_name,
            "info": out if code == 0 else err,
            "error": err if code != 0 else None,
        }

    def get_upgrade_command(self, package: Optional[str] = None) -> List[str]:
        return ["apk", "add", "-u", package] if package else ["apk", "upgrade"]

    def get_install_command(self, package: str) -> List[str]:
        return ["apk", "add", package]

    def get_remove_command(self, package: str) -> List[str]:
        return ["apk", "del", package]


class AptManager(BasePackageManager):
    """Debian, Ubuntu, Linux Mint & Raspberry Pi OS Package Manager (apt/dpkg)."""
    id = "apt"
    name = "APT / dpkg (Debian/Ubuntu/Mint)"
    short_name = "apt"

    def is_available(self) -> bool:
        return bool(shutil.which("dpkg-query") or shutil.which("apt"))

    def get_installed_packages(self) -> List[Dict[str, Any]]:
        # dpkg-query is extraordinarily fast (~15ms)
        code, out, err = run_command(
            ["dpkg-query", "-W", "-f=${Package}\t${Version}\t${Architecture}\n"],
            timeout=20,
        )
        if code != 0:
            return []

        packages = []
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            name = parts[0].strip()
            version = parts[1].strip() if len(parts) > 1 else ""
            arch = parts[2].strip() if len(parts) > 2 else ""
            packages.append({
                "name": name,
                "version": version,
                "arch": arch,
                "full": f"{name} {version}",
            })

        packages.sort(key=lambda p: p["name"].lower())
        return packages

    def get_installed_count(self) -> int:
        code, out, err = run_command(["dpkg-query", "-W", "-f=${Package}\n"], timeout=15)
        if code == 0:
            lines = [l for l in out.splitlines() if l.strip()]
            return len(lines)
        return 0

    def get_upgradable_packages(self) -> List[Dict[str, Any]]:
        code, out, err = run_command(["apt", "list", "--upgradable"], timeout=25)
        if code != 0:
            return [{"error": err or "Failed to check upgradable packages"}]

        packages = []
        for line in out.splitlines():
            line = line.strip()
            if not line or line.startswith("Listing"):
                continue
            # Format: package/suite new_version arch [upgradable from: current_version]
            parts = line.split()
            if len(parts) >= 2:
                name_part = parts[0].split("/")[0]
                new_ver = parts[1]
                arch = parts[2] if len(parts) > 2 and not parts[2].startswith("[") else ""

                current_ver = ""
                m = re.search(r"\[upgradable from:\s*([^\]]+)\]", line)
                if m:
                    current_ver = m.group(1).strip()

                packages.append({
                    "name": name_part,
                    "name_clean": name_part,
                    "version": new_ver,
                    "current_version": current_ver,
                    "arch": arch,
                    "full": line,
                })
        return packages

    def search_packages(self, query: str) -> List[Dict[str, Any]]:
        # First try searching names only
        code, out, err = run_command(
            ["apt-cache", "search", "--names-only", query], timeout=15
        )
        if code != 0 or not out.strip():
            # Fallback to general apt-cache search
            code, out, err = run_command(["apt-cache", "search", query], timeout=15)

        if code != 0:
            return [{"error": err or "Package search failed"}]

        results = []
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(" - ", 1)
            name = parts[0].strip()
            desc = parts[1].strip() if len(parts) > 1 else ""
            results.append({
                "name": name,
                "version": desc,
                "description": desc,
                "full": line,
            })
        return results

    def get_package_info(self, package_name: str) -> Dict[str, Any]:
        # Try installed package query first
        code, out, err = run_command(["dpkg-query", "-s", package_name], timeout=10)
        if code != 0:
            # Fallback to repository package details
            code, out, err = run_command(["apt-cache", "show", package_name], timeout=10)

        return {
            "package": package_name,
            "info": out if code == 0 else err,
            "error": err if code != 0 else None,
        }

    def get_upgrade_command(self, package: Optional[str] = None) -> List[str]:
        if package:
            return ["apt-get", "install", "--only-upgrade", "-y", package]
        return ["apt-get", "upgrade", "-y"]

    def get_install_command(self, package: str) -> List[str]:
        return ["apt-get", "install", "-y", package]

    def get_remove_command(self, package: str) -> List[str]:
        return ["apt-get", "remove", "-y", package]


class PacmanManager(BasePackageManager):
    """Arch Linux, Manjaro & EndeavourOS Package Manager (pacman)."""
    id = "pacman"
    name = "Pacman (Arch/Manjaro)"
    short_name = "pacman"

    def is_available(self) -> bool:
        return bool(shutil.which("pacman"))

    def get_installed_packages(self) -> List[Dict[str, Any]]:
        code, out, err = run_command(["pacman", "-Q"], timeout=20)
        if code != 0:
            return []

        packages = []
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(None, 1)
            name = parts[0]
            version = parts[1] if len(parts) > 1 else ""
            packages.append({"name": name, "version": version, "full": line})
        return packages

    def get_installed_count(self) -> int:
        code, out, err = run_command(["pacman", "-Q"], timeout=15)
        if code == 0:
            return len([l for l in out.splitlines() if l.strip()])
        return 0

    def get_upgradable_packages(self) -> List[Dict[str, Any]]:
        # Use checkupdates if installed (safer than pacman -Sy)
        chk = shutil.which("checkupdates")
        cmd = [chk] if chk else ["pacman", "-Qu"]
        code, out, err = run_command(cmd, timeout=25)
        if code != 0 and code != 1:  # checkupdates exits 1 if no updates
            return []

        packages = []
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            # Format: package old_version -> new_version
            parts = line.split()
            if len(parts) >= 4 and parts[2] == "->":
                packages.append({
                    "name": parts[0],
                    "name_clean": parts[0],
                    "current_version": parts[1],
                    "version": parts[3],
                    "full": line,
                })
        return packages

    def search_packages(self, query: str) -> List[Dict[str, Any]]:
        code, out, err = run_command(["pacman", "-Ss", query], timeout=15)
        if code != 0:
            return [{"error": err or "Package search failed"}]

        results = []
        lines = out.splitlines()
        for i in range(0, len(lines), 2):
            header = lines[i].strip()
            if not header:
                continue
            parts = header.split()
            if len(parts) >= 2:
                name_repo = parts[0]
                name = name_repo.split("/")[-1]
                version = parts[1]
                desc = lines[i + 1].strip() if (i + 1) < len(lines) else ""
                results.append({
                    "name": name,
                    "version": version,
                    "description": desc,
                    "full": header,
                })
        return results

    def get_package_info(self, package_name: str) -> Dict[str, Any]:
        code, out, err = run_command(["pacman", "-Qi", package_name], timeout=10)
        if code != 0:
            code, out, err = run_command(["pacman", "-Si", package_name], timeout=10)
        return {
            "package": package_name,
            "info": out if code == 0 else err,
            "error": err if code != 0 else None,
        }

    def get_upgrade_command(self, package: Optional[str] = None) -> List[str]:
        if package:
            return ["pacman", "-S", "--noconfirm", package]
        return ["pacman", "-Syu", "--noconfirm"]

    def get_install_command(self, package: str) -> List[str]:
        return ["pacman", "-S", "--noconfirm", package]

    def get_remove_command(self, package: str) -> List[str]:
        return ["pacman", "-R", "--noconfirm", package]


class DnfManager(BasePackageManager):
    """Fedora, RHEL, CentOS & Rocky Linux Package Manager (dnf/rpm)."""
    id = "dnf"
    name = "DNF / RPM (Fedora/RHEL)"
    short_name = "dnf"

    def is_available(self) -> bool:
        return bool(shutil.which("dnf") or shutil.which("rpm"))

    def get_installed_packages(self) -> List[Dict[str, Any]]:
        code, out, err = run_command(
            ["rpm", "-qa", "--qf", "%{NAME}\t%{VERSION}-%{RELEASE}\t%{ARCH}\n"],
            timeout=20,
        )
        if code != 0:
            return []

        packages = []
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            name = parts[0].strip()
            version = parts[1].strip() if len(parts) > 1 else ""
            arch = parts[2].strip() if len(parts) > 2 else ""
            packages.append({"name": name, "version": version, "arch": arch, "full": line})

        packages.sort(key=lambda p: p["name"].lower())
        return packages

    def get_installed_count(self) -> int:
        code, out, err = run_command(["rpm", "-qa"], timeout=15)
        if code == 0:
            return len([l for l in out.splitlines() if l.strip()])
        return 0

    def get_upgradable_packages(self) -> List[Dict[str, Any]]:
        code, out, err = run_command(["dnf", "check-update", "-q"], timeout=25)
        # dnf check-update returns 100 if updates are available, 0 if none
        if code not in (0, 100):
            return []

        packages = []
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                version = parts[1]
                packages.append({
                    "name": name,
                    "name_clean": name,
                    "version": version,
                    "full": line,
                })
        return packages

    def search_packages(self, query: str) -> List[Dict[str, Any]]:
        code, out, err = run_command(["dnf", "search", "-q", query], timeout=20)
        if code != 0:
            return [{"error": err or "Package search failed"}]

        results = []
        for line in out.splitlines():
            line = line.strip()
            if not line or line.startswith("="):
                continue
            parts = line.split(" : ", 1)
            name = parts[0].strip()
            desc = parts[1].strip() if len(parts) > 1 else ""
            results.append({"name": name, "version": desc, "description": desc, "full": line})
        return results

    def get_package_info(self, package_name: str) -> Dict[str, Any]:
        code, out, err = run_command(["rpm", "-qi", package_name], timeout=10)
        return {
            "package": package_name,
            "info": out if code == 0 else err,
            "error": err if code != 0 else None,
        }

    def get_upgrade_command(self, package: Optional[str] = None) -> List[str]:
        if package:
            return ["dnf", "upgrade", "-y", package]
        return ["dnf", "upgrade", "-y"]

    def get_install_command(self, package: str) -> List[str]:
        return ["dnf", "install", "-y", package]

    def get_remove_command(self, package: str) -> List[str]:
        return ["dnf", "remove", "-y", package]


class NullPackageManager(BasePackageManager):
    """Fallback when no recognized package manager is available."""
    id = "none"
    name = "No Package Manager Detected"
    short_name = "none"


# Cache active manager instance
_CURRENT_MANAGER: Optional[BasePackageManager] = None


def get_package_manager() -> BasePackageManager:
    """
    Auto-detect and return the active package manager adapter for this host.
    Cached for fast repeated access.
    """
    global _CURRENT_MANAGER
    if _CURRENT_MANAGER is not None:
        return _CURRENT_MANAGER

    # Detection priority:
    # 1. Alpine / postmarketOS (apk)
    if shutil.which("apk"):
        _CURRENT_MANAGER = ApkManager()
        return _CURRENT_MANAGER

    # 2. Debian / Ubuntu / Linux Mint (dpkg / apt)
    if shutil.which("dpkg-query") or shutil.which("apt") or shutil.which("apt-get"):
        _CURRENT_MANAGER = AptManager()
        return _CURRENT_MANAGER

    # 3. Arch Linux / Manjaro (pacman)
    if shutil.which("pacman"):
        _CURRENT_MANAGER = PacmanManager()
        return _CURRENT_MANAGER

    # 4. Fedora / RHEL (dnf / rpm)
    if shutil.which("dnf") or shutil.which("rpm"):
        _CURRENT_MANAGER = DnfManager()
        return _CURRENT_MANAGER

    _CURRENT_MANAGER = NullPackageManager()
    return _CURRENT_MANAGER


# Convenience wrapper functions for API and templates

def get_installed_packages(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """Get full list of installed packages (cached for 60s)."""
    now = time.time()
    if not force_refresh and _PACKAGES_CACHE["installed"] is not None:
        if (now - _PACKAGES_CACHE["timestamp"]) < _PACKAGES_CACHE["ttl"]:
            return _PACKAGES_CACHE["installed"]

    mgr = get_package_manager()
    packages = mgr.get_installed_packages()
    _PACKAGES_CACHE["installed"] = packages
    _PACKAGES_CACHE["timestamp"] = now
    return packages


def get_installed_count() -> int:
    """Get count of installed packages."""
    if _PACKAGES_CACHE["installed"] is not None:
        return len(_PACKAGES_CACHE["installed"])
    return get_package_manager().get_installed_count()


def get_upgradable_packages() -> List[Dict[str, Any]]:
    """Get list of packages that can be upgraded."""
    return get_package_manager().get_upgradable_packages()


def search_packages(query: str) -> List[Dict[str, Any]]:
    """Search for packages in distribution repositories."""
    query = query.strip()
    if not query:
        return []
    return get_package_manager().search_packages(query)


def get_package_info(package_name: str) -> Dict[str, Any]:
    """Get detailed info about a package."""
    return get_package_manager().get_package_info(package_name)


def upgrade_packages(package: Optional[str] = None) -> Dict[str, Any]:
    """Run package upgrade command."""
    invalidate_packages_cache()
    cmd = get_package_manager().get_upgrade_command(package)
    if not cmd:
        return {"success": False, "error": "No upgrade command available for this system"}
    code, out, err = run_sudo_command(cmd, timeout=300)
    return {"success": code == 0, "output": out, "error": err}


def install_package(package_name: str) -> Dict[str, Any]:
    """Run package install command."""
    invalidate_packages_cache()
    cmd = get_package_manager().get_install_command(package_name)
    if not cmd:
        return {"success": False, "error": "No install command available for this system"}
    code, out, err = run_sudo_command(cmd, timeout=180)
    return {"success": code == 0, "output": out, "error": err}


def remove_package(package_name: str) -> Dict[str, Any]:
    """Run package remove command."""
    invalidate_packages_cache()
    cmd = get_package_manager().get_remove_command(package_name)
    if not cmd:
        return {"success": False, "error": "No remove command available for this system"}
    code, out, err = run_sudo_command(cmd, timeout=120)
    return {"success": code == 0, "output": out, "error": err}
