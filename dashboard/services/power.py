"""
Power control operations.
"""
import subprocess

from dashboard.dependencies import run_sudo_command


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
