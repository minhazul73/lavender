"""
Storage and disk management.
"""
import subprocess
import os

from dashboard.dependencies import run_command, run_sudo_command


def get_disk_usage() -> list[dict]:
    """
    Run df -h and return parsed mount information.
    """
    code, out, err = run_command(["df", "-h"], timeout=10)
    if code != 0:
        return [{"error": err}]
    
    mounts = []
    lines = out.split("\n")
    # Skip header line
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 6:
            mounts.append({
                "fs": parts[0],
                "size": parts[1],
                "used": parts[2],
                "avail": parts[3],
                "use_pct": parts[4],
                "mount": parts[5],
            })
    return mounts


def get_mounts() -> list[dict]:
    """
    Read /proc/mounts for detailed mount info.
    """
    mounts = []
    try:
        with open("/proc/mounts", "r") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 4:
                    mounts.append({
                        "source": parts[0],
                        "target": parts[1],
                        "fs": parts[2],
                        "options": parts[3],
                    })
    except Exception:
        pass
    return mounts


def get_dir_usage(paths: list[str] = None, top_n: int = 10) -> list[dict]:
    """
    Get disk usage for top directories.
    paths: list of paths to check (default: /, /home, /var)
    """
    if paths is None:
        paths = ["/", "/home", "/var"]
    
    results = []
    for path in paths:
        if not os.path.exists(path):
            continue
        code, out, err = run_command(
            ["du", "-sh", path + "/*", "--exclude=/proc", "--exclude=/sys", "--exclude=/dev", "--exclude=/run"],
            timeout=30,
        )
        if code == 0:
            dirs = []
            for line in out.split("\n"):
                line = line.strip()
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) == 2:
                    size = parts[0]
                    d = parts[1]
                    # Skip the path prefix
                    if d.startswith(path):
                        d = d[len(path):].lstrip("/")
                    dirs.append({"path": d, "size": size})
            # Sort by size (human readable — simple approach)
            dirs.sort(key=lambda x: x["size"], reverse=True)
            results.append({
                "base_path": path,
                "directories": dirs[:top_n],
            })
    
    return results


def unmount(mount_point: str) -> dict:
    """Unmount a filesystem (requires sudo)."""
    code, out, err = run_sudo_command(["umount", mount_point], timeout=15)
    return {
        "success": code == 0,
        "mount": mount_point,
        "output": out,
        "error": err,
    }
