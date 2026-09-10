"""
SSH Loopback Bridge.
Spawns and manages authenticated Linux user sessions over localhost SSH.
All user operations and privileged actions execute in the user's authentic Linux environment.
"""
import shlex
import logging
import asyncio
from typing import Optional
import asyncssh

from dashboard.config import (
    SSH_LOOPBACK_HOST,
    SSH_LOOPBACK_PORT,
    SSH_LOGIN_TIMEOUT,
)

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Raised when Linux credentials fail authentication."""
    pass


class BridgeConnectionError(Exception):
    """Raised when SSH daemon cannot be reached on loopback."""
    pass


async def open_ssh_session(username: str, password: str) -> tuple[asyncssh.SSHClientConnection, dict]:
    """
    Establish an SSH session to the local host using the user's credentials.
    Returns (connection, user_profile_dict).
    """
    try:
        conn = await asyncssh.connect(
            host=SSH_LOOPBACK_HOST,
            port=SSH_LOOPBACK_PORT,
            username=username,
            password=password,
            known_hosts=None,  # localhost loopback only
            login_timeout=SSH_LOGIN_TIMEOUT,
        )
    except asyncssh.PermissionDenied as exc:
        logger.warning("SSH auth failed for user %s: %s", username, exc)
        raise AuthError("Invalid username or password.") from exc
    except (OSError, asyncssh.Error) as exc:
        logger.error("SSH connection to %s:%s failed: %s", SSH_LOOPBACK_HOST, SSH_LOOPBACK_PORT, exc)
        raise BridgeConnectionError(
            f"Unable to connect to SSH on {SSH_LOOPBACK_HOST}:{SSH_LOOPBACK_PORT}. "
            "Please ensure sshd is running."
        ) from exc

    # Gather user environment information directly from the established session
    try:
        probe = await conn.run("id -u; id -g; id -Gn; echo \"$HOME\"; echo \"$SHELL\"", timeout=5, check=False)
        lines = [line.strip() for line in probe.stdout.strip().split("\n") if line.strip()]
        
        uid = int(lines[0]) if len(lines) > 0 and lines[0].isdigit() else 1000
        gid = int(lines[1]) if len(lines) > 1 and lines[1].isdigit() else 1000
        groups = lines[2].split() if len(lines) > 2 else []
        home = lines[3] if len(lines) > 3 else f"/home/{username}"
        shell = lines[4] if len(lines) > 4 else "/bin/sh"

        user_info = {
            "uid": uid,
            "gid": gid,
            "groups": groups,
            "home": home,
            "shell": shell,
        }
    except Exception as exc:
        logger.warning("Failed to probe user info for %s over SSH: %s", username, exc)
        user_info = {
            "uid": 1000,
            "gid": 1000,
            "groups": [],
            "home": f"/home/{username}",
            "shell": "/bin/sh",
        }

    return conn, user_info


async def ssh_run(
    conn: asyncssh.SSHClientConnection,
    cmd: list[str] | str,
    timeout: int = 30,
) -> tuple[int, str, str]:
    """
    Execute a command inside the authenticated user's session over SSH.
    Returns (returncode, stdout, stderr).
    """
    cmd_str = shlex.join(cmd) if isinstance(cmd, list) else cmd
    try:
        result = await conn.run(cmd_str, timeout=timeout, check=False)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except asyncio.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


async def ssh_run_user_service(
    conn: asyncssh.SSHClientConnection,
    uid: int,
    cmd: list[str],
    timeout: int = 30,
) -> tuple[int, str, str]:
    """
    Execute a systemctl --user command ensuring proper XDG and D-Bus runtime variables.
    Prevents 'Failed to connect to bus: No such file or directory' errors.
    """
    env_prefix = (
        f"env XDG_RUNTIME_DIR=/run/user/{uid} "
        f"DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{uid}/systemd/private "
    )
    cmd_str = env_prefix + shlex.join(cmd)
    return await ssh_run(conn, cmd_str, timeout=timeout)


async def verify_sudo_password(conn: asyncssh.SSHClientConnection, password: str) -> tuple[bool, str]:
    """
    Verify user password with sudo and refresh Linux sudo timestamp ticket.
    Runs `sudo -S -p '' -v` piping password via stdin.
    """
    try:
        result = await conn.run(
            "sudo -S -p '' -v",
            input=f"{password}\n",
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            return True, ""
        err = result.stderr.strip() or result.stdout.strip()
        return False, err or "Invalid password or user is not authorized in sudoers"
    except Exception as exc:
        return False, str(exc)


async def ssh_run_sudo(
    conn: asyncssh.SSHClientConnection,
    cmd: list[str],
    password: Optional[str] = None,
    timeout: int = 30,
) -> tuple[int, str, str]:
    """
    Execute a privileged command with sudo over the user's SSH session.
    If password is provided, pipes it to `sudo -S`.
    If password is None, uses `sudo -n` (non-interactive) relying on active elevation ticket or NOPASSWD.
    """
    cmd_joined = shlex.join(cmd)
    if password:
        full_cmd = f"sudo -S -p '' {cmd_joined}"
        stdin_input = f"{password}\n"
    else:
        full_cmd = f"sudo -n {cmd_joined}"
        stdin_input = None

    try:
        result = await conn.run(full_cmd, input=stdin_input, timeout=timeout, check=False)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except asyncio.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


async def drop_sudo_ticket(conn: asyncssh.SSHClientConnection) -> None:
    """Revoke sudo timestamp ticket (`sudo -k`)."""
    try:
        await conn.run("sudo -k", timeout=5, check=False)
    except Exception:
        pass
