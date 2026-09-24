"""
System and user privilege introspection utilities.
"""
import os
import shutil
from typing import Optional

from server.core.executor import get_executor


def which(program: str) -> Optional[str]:
    """Find program in PATH, return full path or None."""
    return shutil.which(program)


def get_current_user_info() -> dict:
    """Get info about the current executing user."""
    info = {"uid": os.getuid(), "gid": os.getgid(), "groups": []}
    executor = get_executor()
    try:
        res = executor.run_sync(["id"], timeout=5)
        info["id_output"] = res.stdout.strip()
    except Exception:
        info["id_output"] = "unknown"
    try:
        res = executor.run_sync(["groups"], timeout=5)
        info["groups"] = res.stdout.strip().split()
    except Exception:
        info["groups"] = []
    return info


def read_sudoers(path: str = "/etc/sudoers") -> str:
    """Read /etc/sudoers content (read-only)."""
    try:
        with open(path, "r", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def visudo_check() -> tuple[bool, str]:
    """Run visudo -c to check sudoers syntax safely without blocking."""
    executor = get_executor()
    res = executor.run_sync(["sudo", "-n", "visudo", "-c"], timeout=2)
    return res.returncode == 0, (res.stdout or res.stderr or ("Requires elevated password" if res.returncode != 0 else "OK"))
