"""
Backward-compatibility layer for server.dependencies.
Forwards to server.core.executor, server.utils, and server.auth.
"""
import os
from typing import Optional

from server.core.config import SUDO_COMMANDS
from server.core.executor import get_executor
from server.utils.cmd import which
from server.utils.passwd import (
    NON_LOGIN_SHELLS,
    parse_passwd_users,
    parse_all_passwd_users,
    parse_groups,
)
from server.utils.sessions import (
    parse_active_sessions,
    parse_login_history,
)
from server.utils.system import (
    get_current_user_info,
    read_sudoers,
    visudo_check,
)


def run_command(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Backward-compatible run_command returning (returncode, stdout, stderr)."""
    res = get_executor().run_sync(cmd, timeout=float(timeout))
    return res.returncode, res.stdout, res.stderr


def run_sudo_command(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Run a command with sudo. Returns (returncode, stdout, stderr)."""
    full_cmd = ["sudo"] + cmd
    return run_command(full_cmd, timeout)


async def run_session_command(
    session: Optional["UserSession"],
    cmd: list[str],
    timeout: int = 30,
) -> tuple[int, str, str]:
    """Run command over authenticated user's session."""
    from server.auth.bridge import run_command_async
    if session:
        return await run_command_async(cmd, timeout=timeout)
    return run_command(cmd, timeout=timeout)


async def run_session_user_service(
    session: Optional["UserSession"],
    cmd: list[str],
    timeout: int = 30,
) -> tuple[int, str, str]:
    """Run user systemd service command."""
    from server.auth.bridge import run_user_service_async
    uid = session.uid if session else os.getuid()
    return await run_user_service_async(uid, cmd, timeout=timeout)


async def run_session_sudo(
    session: Optional["UserSession"],
    cmd: list[str],
    password: Optional[str] = None,
    timeout: int = 30,
) -> tuple[int, str, str]:
    """Run privileged command with sudo over user's session."""
    from server.auth.bridge import run_sudo_async
    return await run_sudo_async(cmd, password=password, timeout=timeout)


__all__ = [
    "SUDO_COMMANDS",
    "run_command",
    "run_sudo_command",
    "run_session_command",
    "run_session_user_service",
    "run_session_sudo",
    "which",
    "NON_LOGIN_SHELLS",
    "parse_passwd_users",
    "parse_all_passwd_users",
    "parse_groups",
    "parse_active_sessions",
    "parse_login_history",
    "get_current_user_info",
    "read_sudoers",
    "visudo_check",
]
