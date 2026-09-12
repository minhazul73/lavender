"""
Dual-Engine Authentication Bridge for Linux Systems.
Supports:
1. Primary: SSH Loopback Bridge (when OpenSSH daemon is running)
2. Fallback: Native Linux PAM & System Auth (for UI devices, tablets, kiosks without SSH)
All user operations and privileged actions execute in the user's authentic Linux environment.
"""
import os
import pwd
import grp
import socket
import shlex
import logging
import asyncio
import subprocess
from typing import Optional
import asyncssh

from dashboard.config import (
    SSH_LOOPBACK_HOST,
    SSH_LOOPBACK_PORT,
    SSH_LOGIN_TIMEOUT,
    AUTH_FALLBACK_TO_LOCAL,
    PAM_SERVICE,
)

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Raised when Linux credentials fail authentication."""
    pass


class BridgeConnectionError(Exception):
    """Raised when SSH daemon cannot be reached on loopback."""
    pass


def is_ssh_available(host: str = SSH_LOOPBACK_HOST, port: int = SSH_LOOPBACK_PORT, timeout: float = 0.25) -> bool:
    """Quickly probe if SSH daemon is listening on host:port."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False


# ==========================================
# Engine 1: SSH Loopback Bridge
# ==========================================

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
    """Execute a command inside the authenticated user's session over SSH."""
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
    """Execute a systemctl --user command ensuring proper XDG and D-Bus runtime variables."""
    env_prefix = (
        f"env XDG_RUNTIME_DIR=/run/user/{uid} "
        f"DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{uid}/systemd/private "
    )
    cmd_str = env_prefix + shlex.join(cmd)
    return await ssh_run(conn, cmd_str, timeout=timeout)


async def verify_sudo_password(conn: asyncssh.SSHClientConnection, password: str) -> tuple[bool, str]:
    """Verify user password with sudo and refresh Linux sudo timestamp ticket."""
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
    """Execute a privileged command with sudo over the user's SSH session."""
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


# ==========================================
# Engine 2: Local PAM / Native Linux Auth Fallback
# ==========================================

def get_local_user_info(username: str) -> dict:
    """Look up local user details via pwd and grp."""
    try:
        pw = pwd.getpwnam(username)
    except KeyError:
        raise AuthError(f"User '{username}' does not exist on this system.")

    groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
    try:
        primary_group = grp.getgrgid(pw.pw_gid).gr_name
        if primary_group not in groups:
            groups.insert(0, primary_group)
    except Exception:
        pass

    return {
        "uid": pw.pw_uid,
        "gid": pw.pw_gid,
        "groups": groups,
        "home": pw.pw_dir,
        "shell": pw.pw_shell,
    }


def verify_linux_credentials_local(username: str, password: str) -> bool:
    """
    Verify user credentials directly on the Linux host without SSH.
    Checks:
    1. Direct PAM authentication via python-pam
    2. Sudo validation (sudo -S -p '' -k -v)
    3. Su validation (/bin/su -c true)
    """
    if not password:
        return False

    # 1. PAM authentication
    try:
        import pam
        p = pam.pam()
        services_to_try = [PAM_SERVICE, "login", "common-auth", "passwd", "sudo"]
        for s in set(services_to_try):
            try:
                if p.authenticate(username, password, service=s):
                    return True
            except Exception:
                pass
    except Exception as exc:
        logger.debug("PAM library auth failed or unavailable: %s", exc)

    # 2. Sudo validation (works if user is in wheel/sudo group)
    try:
        proc = subprocess.run(
            ["sudo", "-S", "-p", "", "-k", "-v"],
            input=f"{password}\n",
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0:
            return True
    except Exception:
        pass

    # 3. /bin/su validation (setuid root on all Linux distros)
    for su_bin in ["/bin/su", "/usr/bin/su"]:
        if os.path.isfile(su_bin):
            try:
                proc = subprocess.run(
                    [su_bin, "-c", "true", username],
                    input=f"{password}\n",
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if proc.returncode == 0:
                    return True
            except Exception:
                pass

    return False


async def open_local_session(username: str, password: str) -> dict:
    """
    Authenticate a user locally via PAM/shadow and return their user info.
    """
    user_info = get_local_user_info(username)
    is_valid = await asyncio.to_thread(verify_linux_credentials_local, username, password)
    if not is_valid:
        raise AuthError("Invalid username or password.")
    return user_info


async def local_run(cmd: list[str] | str, timeout: int = 30) -> tuple[int, str, str]:
    """Execute a local command asynchronously."""
    try:
        if isinstance(cmd, str):
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        else:
            proc = await asyncio.create_subprocess_exec(
                cmd[0], *cmd[1:],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode or 0, stdout.decode().strip(), stderr.decode().strip()
    except asyncio.TimeoutExpired:
        try:
            proc.kill()
        except Exception:
            pass
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


async def local_run_user_service(uid: int, cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Execute a local systemctl --user command with correct XDG and D-Bus runtime variables."""
    env = os.environ.copy()
    env["XDG_RUNTIME_DIR"] = f"/run/user/{uid}"
    env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{uid}/systemd/private"
    try:
        proc = await asyncio.create_subprocess_exec(
            cmd[0], *cmd[1:],
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode or 0, stdout.decode().strip(), stderr.decode().strip()
    except asyncio.TimeoutExpired:
        try:
            proc.kill()
        except Exception:
            pass
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


async def local_verify_sudo_password(password: str) -> tuple[bool, str]:
    """Validate password via local sudo -S -v."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "sudo", "-S", "-p", "", "-v",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=f"{password}\n".encode()),
            timeout=10,
        )
        if proc.returncode == 0:
            return True, ""
        err = stderr.decode().strip() or stdout.decode().strip()
        return False, err or "Invalid password or user is not authorized in sudoers"
    except Exception as e:
        return False, str(e)


async def local_run_sudo(
    cmd: list[str],
    password: Optional[str] = None,
    timeout: int = 30,
) -> tuple[int, str, str]:
    """Execute a local sudo command."""
    if password:
        full_cmd = ["sudo", "-S", "-p", ""] + cmd
        stdin_input = f"{password}\n".encode()
    else:
        full_cmd = ["sudo", "-n"] + cmd
        stdin_input = None

    try:
        proc = await asyncio.create_subprocess_exec(
            full_cmd[0], *full_cmd[1:],
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=stdin_input),
            timeout=timeout,
        )
        return proc.returncode or 0, stdout.decode().strip(), stderr.decode().strip()
    except asyncio.TimeoutExpired:
        try:
            proc.kill()
        except Exception:
            pass
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


async def local_drop_sudo_ticket() -> None:
    """Drop local sudo timestamp ticket."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "sudo", "-k",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
    except Exception:
        pass


# ==========================================
# Unified Router & Session Facade
# ==========================================

async def authenticate_user(username: str, password: str) -> tuple[str, Optional[asyncssh.SSHClientConnection], dict]:
    """
    Authenticate user using best available engine:
    1. SSH Loopback if sshd is running
    2. Local PAM / system auth fallback if SSH is not running
    Returns (auth_mode, ssh_conn, user_info).
    """
    ssh_up = await asyncio.to_thread(is_ssh_available, SSH_LOOPBACK_HOST, SSH_LOOPBACK_PORT)
    if ssh_up:
        try:
            conn, user_info = await open_ssh_session(username, password)
            return "ssh", conn, user_info
        except BridgeConnectionError as exc:
            if not AUTH_FALLBACK_TO_LOCAL:
                raise
            logger.info("SSH bridge error (%s), falling back to local PAM authentication", exc)
        except AuthError:
            # Explicit bad password on SSH should not fallback
            raise

    if not AUTH_FALLBACK_TO_LOCAL:
        raise BridgeConnectionError(
            f"Unable to connect to SSH on {SSH_LOOPBACK_HOST}:{SSH_LOOPBACK_PORT}. "
            "Please ensure sshd is running."
        )

    logger.info("Authenticating user %s via local PAM engine", username)
    user_info = await open_local_session(username, password)
    return "local", None, user_info


async def run_session_cmd(session, cmd: list[str] | str, timeout: int = 30) -> tuple[int, str, str]:
    """Execute command routing to SSH or Local depending on active session."""
    if session and session.ssh_conn and not getattr(session.ssh_conn, "is_closing", lambda: False)():
        return await ssh_run(session.ssh_conn, cmd, timeout=timeout)
    return await local_run(cmd, timeout=timeout)


async def run_session_user_unit(session, cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Execute systemctl --user command routing to SSH or Local."""
    if session and session.ssh_conn and not getattr(session.ssh_conn, "is_closing", lambda: False)():
        return await ssh_run_user_service(session.ssh_conn, session.uid, cmd, timeout=timeout)
    uid = session.uid if session else os.getuid()
    return await local_run_user_service(uid, cmd, timeout=timeout)


async def verify_session_sudo(session, password: str) -> tuple[bool, str]:
    """Validate user password with sudo routing to SSH or Local."""
    if session and session.ssh_conn and not getattr(session.ssh_conn, "is_closing", lambda: False)():
        return await verify_sudo_password(session.ssh_conn, password)
    return await local_verify_sudo_password(password)


async def run_session_elevated(
    session,
    cmd: list[str],
    password: Optional[str] = None,
    timeout: int = 30,
) -> tuple[int, str, str]:
    """Execute sudo command routing to SSH or Local."""
    if session and session.ssh_conn and not getattr(session.ssh_conn, "is_closing", lambda: False)():
        return await ssh_run_sudo(session.ssh_conn, cmd, password=password, timeout=timeout)
    return await local_run_sudo(cmd, password=password, timeout=timeout)


async def drop_session_sudo(session) -> None:
    """Drop sudo ticket routing to SSH or Local."""
    if session and session.ssh_conn:
        await drop_sudo_ticket(session.ssh_conn)
    await local_drop_sudo_ticket()
