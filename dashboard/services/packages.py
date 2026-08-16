"""
Package management using apk.
"""
import subprocess

from dashboard.dependencies import run_command, run_sudo_command


def get_installed_count() -> int:
    """Get count of installed packages."""
    code, out, err = run_command(["apk", "info"], timeout=15)
    if code == 0:
        return len(out.split("\n"))
    return 0


def get_upgradable_packages() -> list[dict]:
    """
    Get list of packages that can be upgraded.
    """
    code, out, err = run_command(["apk", "list", "--upgradable"], timeout=15)
    if code != 0:
        return [{"error": err}]
    
    packages = []
    for line in out.split("\n"):
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
                    pkg_info["version"] = name_ver[1]
                    pkg_info["arch"] = name_ver[2]
                else:
                    pkg_info["name_clean"] = parts[0]
            else:
                pkg_info["name_clean"] = parts[0]
            
            # Check for upgradable from
            if "[upgradable from:" in line:
                m = __import__("re").search(r"\[upgradable from:\s*([^\]]+)\]", line)
                if m:
                    pkg_info["current_version"] = m.group(1).strip()
            
            packages.append(pkg_info)
    
    return packages


def upgrade_packages() -> dict:
    """
    Run apk upgrade (requires sudo).
    """
    code, out, err = run_sudo_command(["apk", "upgrade"], timeout=300)
    return {
        "success": code == 0,
        "output": out,
        "error": err,
    }


def search_packages(query: str) -> list[dict]:
    """Search for packages by name."""
    code, out, err = run_command(["apk", "search", query], timeout=15)
    if code != 0:
        return [{"error": err}]
    
    results = []
    for line in out.split("\n"):
        line = line.strip()
        if line:
            results.append({"name": line})
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
