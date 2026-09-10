"""
Shared dependencies and utility functions for the Device Dashboard.
"""
import subprocess
import shutil
import os
from typing import Optional

from dashboard.config import SUDO_COMMANDS


def run_command(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """
    Run a command and return (returncode, stdout, stderr).
    cmd should be a list of arguments.
    
    Preserves XDG_RUNTIME_DIR and DBUS_SESSION_BUS_ADDRESS from the
    parent environment so systemctl --user commands work correctly.
    """
    try:
        env = os.environ.copy()
        # Ensure XDG_RUNTIME_DIR is set for systemd --user commands
        if "XDG_RUNTIME_DIR" not in env:
            uid = os.getuid()
            env["XDG_RUNTIME_DIR"] = f"/run/user/{uid}"
        if "DBUS_SESSION_BUS_ADDRESS" not in env:
            rd = env.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
            env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={rd}/systemd/private"
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"
    except Exception as e:
        return -1, "", str(e)


def run_sudo_command(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """
    Run a command with sudo. Returns (returncode, stdout, stderr).
    Note: This will prompt for a password if sudo requires interactive auth.
    """
    full_cmd = ["sudo"] + cmd
    return run_command(full_cmd, timeout)


async def run_session_command(
    session: Optional["UserSession"],
    cmd: list[str],
    timeout: int = 30,
) -> tuple[int, str, str]:
    """
    Run command over authenticated user's SSH loopback session if available,
    otherwise fallback to local subprocess.
    """
    from dashboard.auth.bridge import ssh_run
    if session and session.ssh_conn and not getattr(session.ssh_conn, "is_closing", lambda: False)():
        return await ssh_run(session.ssh_conn, cmd, timeout=timeout)
    return run_command(cmd, timeout=timeout)


async def run_session_user_service(
    session: Optional["UserSession"],
    cmd: list[str],
    timeout: int = 30,
) -> tuple[int, str, str]:
    """
    Run user systemd service command (systemctl --user ...) ensuring
    XDG_RUNTIME_DIR and DBUS variables match the session's UID.
    """
    from dashboard.auth.bridge import ssh_run_user_service
    if session and session.ssh_conn and not getattr(session.ssh_conn, "is_closing", lambda: False)():
        return await ssh_run_user_service(session.ssh_conn, session.uid, cmd, timeout=timeout)
    return run_command(cmd, timeout=timeout)


async def run_session_sudo(
    session: Optional["UserSession"],
    cmd: list[str],
    password: Optional[str] = None,
    timeout: int = 30,
) -> tuple[int, str, str]:
    """
    Run privileged command with sudo over the user's SSH session.
    """
    from dashboard.auth.bridge import ssh_run_sudo
    if session and session.ssh_conn and not getattr(session.ssh_conn, "is_closing", lambda: False)():
        return await ssh_run_sudo(session.ssh_conn, cmd, password=password, timeout=timeout)
    return run_sudo_command(cmd, timeout=timeout)



def which(program: str) -> Optional[str]:
    """Find program in PATH, return full path or None."""
    return shutil.which(program)


def parse_passwd_users(min_uid: int = 1000) -> list[dict]:
    """Parse /etc/passwd and return human users (uid >= min_uid)."""
    users = []
    try:
        with open("/etc/passwd", "r") as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) >= 7:
                    uid = int(parts[2])
                    if uid >= min_uid:
                        users.append({
                            "name": parts[0],
                            "uid": uid,
                            "gid": int(parts[3]),
                            "home": parts[5],
                            "shell": parts[6],
                            "comment": parts[4],
                        })
    except Exception:
        pass
    return users


def parse_groups() -> list[dict]:
    """Parse /etc/group and return all groups."""
    groups = []
    try:
        with open("/etc/group", "r") as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) >= 4:
                    groups.append({
                        "name": parts[0],
                        "gid": int(parts[2]),
                        "members": parts[3].split(",") if parts[3] else [],
                    })
    except Exception:
        pass
    return groups


def get_current_user_info() -> dict:
    """Get info about the current user."""
    info = {"uid": os.getuid(), "gid": os.getgid(), "groups": []}
    try:
        result = subprocess.run(["id"], capture_output=True, text=True, timeout=5)
        info["id_output"] = result.stdout.strip()
    except Exception:
        info["id_output"] = "unknown"
    try:
        result = subprocess.run(["groups"], capture_output=True, text=True, timeout=5)
        info["groups"] = result.stdout.strip().split()
    except Exception:
        info["groups"] = []
    return info


def read_sudoers() -> str:
    """Read /etc/sudoers content (read-only)."""
    try:
        with open("/etc/sudoers", "r") as f:
            return f.read()
    except Exception:
        return ""


def visudo_check() -> tuple[bool, str]:
    """Run visudo -c to check sudoers syntax."""
    code, out, err = run_command(["sudo", "visudo", "-c"], timeout=10)
    return code == 0, out + err
