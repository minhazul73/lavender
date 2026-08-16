"""
Systemd service management.
"""
import subprocess
import re
from typing import Optional

from dashboard.dependencies import run_command, run_sudo_command


def list_services(user_only: bool = False, system_only: bool = False) -> list[dict]:
    """
    List systemd services.
    user_only: only user services (systemctl --user)
    system_only: only system services (systemctl, may need sudo)
    If both false: list both user and system.
    """
    results = []
    
    if not system_only:
        # User services
        code, out, err = run_command(["systemctl", "--user", "list-units", "--type=service", "--all", "--no-pager", "--no-legend"], timeout=15)
        if code == 0:
            for line in out.split("\n"):
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 4:
                    results.append({
                        "name": parts[0],
                        "load_state": parts[1],
                        "active_state": parts[2],
                        "sub_state": parts[3],
                        "scope": "user",
                    })
    
    if not user_only:
        # System services — may need sudo for full list
        code, out, err = run_command(["systemctl", "list-units", "--type=service", "--all", "--no-pager", "--no-legend"], timeout=15)
        if code != 0:
            # Try with sudo
            code, out, err = run_sudo_command(["systemctl", "list-units", "--type=service", "--all", "--no-pager", "--no-legend"], timeout=15)
        if code == 0:
            for line in out.split("\n"):
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 4:
                    results.append({
                        "name": parts[0],
                        "load_state": parts[1],
                        "active_state": parts[2],
                        "sub_state": parts[3],
                        "scope": "system",
                    })
    
    return results


def get_service_status(service_name: str, user: bool = False) -> dict:
    """Get detailed status for a single service."""
    cmd = ["systemctl", "--user", "status", service_name, "--no-pager"] if user else ["systemctl", "status", service_name, "--no-pager"]
    code, out, err = run_command(cmd, timeout=15)
    
    # Try with sudo for system services
    if code != 0 and not user:
        code, out, err = run_sudo_command(cmd, timeout=15)
    
    # Parse key info
    info = {
        "name": service_name,
        "user": user,
        "output": out,
        "error": err,
        "active": False,
        "sub_state": "",
        "main_pid": None,
        "memory": "",
        "cpu": "",
    }
    
    # Parse from output
    for line in out.split("\n"):
        if "Active:" in line:
            info["active"] = "active" in line.lower()
            m = re.search(r"Active:\s+(\w+)", line)
            if m:
                info["sub_state"] = m.group(1)
        m = re.search(r"Main\s+PID:\s+(\d+)", line)
        if m:
            info["main_pid"] = int(m.group(1))
        m = re.search(r"Memory:\s+(.+)", line)
        if m:
            info["memory"] = m.group(1).strip()
        m = re.search(r"CPU:\s+(.+)", line)
        if m:
            info["cpu"] = m.group(1).strip()
    
    return info


def get_service_logs(service_name: str, lines: int = 50, user: bool = False) -> str:
    """Get recent logs for a service."""
    cmd = ["journalctl", "--user", "-u", service_name, "-n", str(lines), "--no-pager", "--output=short"] if user else ["journalctl", "-u", service_name, "-n", str(lines), "--no-pager", "--output=short"]
    code, out, err = run_command(cmd, timeout=15)
    if code != 0 and not user:
        code, out, err = run_sudo_command(cmd, timeout=15)
    if code == 0:
        return out
    return err or "No logs available"


def service_action(service_name: str, action: str, user: bool = False) -> dict:
    """
    Start, stop, restart, or toggle a service.
    action: "start", "stop", "restart", "enable", "disable"
    """
    if user:
        cmd = ["systemctl", "--user", action, service_name]
        code, out, err = run_command(cmd, timeout=15)
    else:
        cmd = ["systemctl", action, service_name]
        code, out, err = run_sudo_command(cmd, timeout=15)
    
    return {
        "action": action,
        "service": service_name,
        "success": code == 0,
        "output": out,
        "error": err,
    }


def service_toggle_enabled(service_name: str, enable: bool, user: bool = False) -> dict:
    """Enable or disable a service."""
    action = "enable" if enable else "disable"
    return service_action(service_name, action, user)


def get_all_units() -> list[dict]:
    """Get all systemd units (not just active) for the full list."""
    # User units
    units = []
    code, out, err = run_command(["systemctl", "--user", "list-units", "--all", "--no-pager", "--no-legend"], timeout=15)
    if code == 0:
        for line in out.split("\n"):
            line = line.strip()
            if not line or line.startswith("UNIT"):
                continue
            parts = line.split()
            if len(parts) >= 4:
                units.append({
                    "name": parts[0],
                    "load": parts[1],
                    "active": parts[2],
                    "sub": parts[3],
                    "scope": "user",
                })
    
    # System units
    code, out, err = run_sudo_command(["systemctl", "list-units", "--all", "--no-pager", "--no-legend"], timeout=15)
    if code == 0:
        for line in out.split("\n"):
            line = line.strip()
            if not line or line.startswith("UNIT"):
                continue
            parts = line.split()
            if len(parts) >= 4:
                units.append({
                    "name": parts[0],
                    "load": parts[1],
                    "active": parts[2],
                    "sub": parts[3],
                    "scope": "system",
                })
    
    return units
