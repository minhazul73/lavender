"""
Power control operations.
"""
import subprocess

from server.dependencies import run_command, run_sudo_command


def reboot() -> dict:
    """Reboot the system (requires sudo)."""
    code, out, err = run_sudo_command(["systemctl", "reboot"], timeout=30)
    return {
        "action": "reboot",
        "success": code == 0,
        "output": out,
        "error": err,
    }


def poweroff() -> dict:
    """Power off the system (requires sudo)."""
    code, out, err = run_sudo_command(["systemctl", "poweroff"], timeout=30)
    return {
        "action": "poweroff",
        "success": code == 0,
        "output": out,
        "error": err,
    }


def suspend() -> dict:
    """Suspend the system (requires sudo)."""
    code, out, err = run_sudo_command(["systemctl", "suspend"], timeout=30)
    return {
        "action": "suspend",
        "success": code == 0,
        "output": out,
        "error": err,
    }


def get_scheduled_shutdown() -> dict:
    """Check if there is a pending scheduled shutdown or reboot."""
    code, out, err = run_command(["shutdown", "--show"], timeout=5)
    if code == 0 and out.strip():
        return {"scheduled": True, "details": out.strip()}
    return {"scheduled": False, "details": None}


def schedule_power_action(action: str, minutes: int, message: str = "") -> dict:
    """Schedule a reboot or poweroff in N minutes (requires sudo)."""
    flag = "-r" if action == "reboot" else "-h"
    cmd = ["shutdown", flag, f"+{minutes}"]
    if message:
        cmd.append(message)
    code, out, err = run_sudo_command(cmd, timeout=10)
    return {
        "success": code == 0,
        "action": action,
        "minutes": minutes,
        "output": out,
        "error": err,
    }


def cancel_scheduled_action() -> dict:
    """Cancel any pending scheduled shutdown or reboot (requires sudo)."""
    code, out, err = run_sudo_command(["shutdown", "-c"], timeout=10)
    return {
        "success": code == 0,
        "output": out,
        "error": err,
    }

