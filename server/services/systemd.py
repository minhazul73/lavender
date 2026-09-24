"""
Systemd service management.
"""
import subprocess
import re
from typing import Optional

from server.dependencies import run_command, run_sudo_command


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
                line = line.lstrip("●* ").strip()
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
                line = line.lstrip("●* ").strip()
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
    
    # Try with sudo for system services only if direct failed completely (no output returned)
    if not out.strip() and not user:
        sudo_code, sudo_out, sudo_err = run_sudo_command(cmd, timeout=15)
        if sudo_out.strip():
            code, out, err = sudo_code, sudo_out, sudo_err
    
    # Parse key info
    info = {
        "name": service_name,
        "user": user,
        "output": out,
        "error": err,
        "active": False,
        "active_state": "inactive",
        "sub_state": "",
        "description": "",
        "unit_file_state": "",
        "since": "",
        "tasks": "",
        "main_pid": None,
        "process_name": "",
        "memory": "",
        "cpu": "",
        "docs": "",
    }
    
    if out.strip():
        first_line = out.strip().split("\n")[0]
        desc_m = re.search(r"^[●○×*]?\s*[\w\.\@\-]+\s*-\s*(.+)$", first_line)
        if desc_m:
            info["description"] = desc_m.group(1).strip()
    
    # Parse from output
    for line in out.split("\n"):
        if "Loaded:" in line:
            m = re.search(r";\s*(enabled|disabled|static|masked|indirect|generated)\b", line)
            if m:
                info["unit_file_state"] = m.group(1)
        if "Active:" in line:
            m = re.search(r"Active:\s+([a-zA-Z\-]+)(?:\s+\(([^)]+)\))?(?:;\s*(.+)|(?:\s+since\s+(.+)))?", line)
            if m:
                primary_state = m.group(1).lower()
                info["active_state"] = primary_state
                info["active"] = primary_state == "active"
                if m.group(2):
                    info["sub_state"] = m.group(2).strip()
                since_val = m.group(3) or m.group(4)
                if since_val:
                    info["since"] = since_val.strip()
        m = re.search(r"Main\s+PID:\s+(\d+)(?:\s+\(([^)]+)\))?", line)
        if m:
            info["main_pid"] = int(m.group(1))
            if m.group(2):
                info["process_name"] = m.group(2).strip()
        m = re.search(r"Tasks:\s+(\d+)", line)
        if m:
            info["tasks"] = m.group(1).strip()
        m = re.search(r"Memory:\s+(.+)", line)
        if m:
            info["memory"] = m.group(1).strip()
        m = re.search(r"CPU:\s+(.+)", line)
        if m:
            info["cpu"] = m.group(1).strip()
        m = re.search(r"Docs:\s+(.+)", line)
        if m:
            info["docs"] = m.group(1).strip()
    
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
        # Try direct first (some operations work without sudo)
        code, out, err = run_command(cmd, timeout=15)
        # If direct failed, try with sudo
        if code != 0:
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
            line = line.lstrip("●* ").strip()
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
            line = line.lstrip("●* ").strip()
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


def get_recent_logs(lines: int = 20) -> list[dict]:
    """Get recent system journal entries as structured data."""
    code, out, err = run_command(
        ["journalctl", "-n", str(lines), "--no-pager", "--output=json"],
        timeout=10,
    )
    if code != 0:
        return []

    logs = []
    for raw_line in out.strip().split("\n"):
        if not raw_line:
            continue
        import json as _json
        try:
            entry = _json.loads(raw_line)
        except Exception:
            continue
        # Extract timestamp
        ts = entry.get("__REALTIME_TIMESTAMP", "")
        # Format as HH:MM:SS
        timestamp = ""
        if ts and "T" in ts:
            try:
                timestamp = ts.split("T")[1][:8]
            except Exception:
                timestamp = ts[-8:]
        elif ts:
            timestamp = ts[-8:]
        else:
            timestamp = "--:--"

        message = entry.get("MESSAGE", "").strip()
        if isinstance(message, list):
            message = " ".join(str(m) for m in message)
        if len(message) > 200:
            message = message[:200] + "…"

        # Determine severity
        priority = int(entry.get("PRIORITY", 6))
        level = "info"
        if priority <= 2:
            level = "error"
        elif priority <= 4:
            level = "warning"
        elif priority <= 6:
            level = "info"

        # Determine service from _SYSTEMD_UNIT
        service = entry.get("_SYSTEMD_UNIT", entry.get("SYSLOG_IDENTIFIER", ""))
        if not service:
            service = entry.get("_COMM", "system")

        logs.append({
            "timestamp": timestamp,
            "message": message,
            "service": service,
            "level": level,
        })

    return logs
