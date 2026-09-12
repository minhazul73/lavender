"""
Native Linux PAM Authentication & Execution Engine.
Directly interfaces with Linux PAM (/lib/security / pam_unix) and local systemd sessions.
Eliminates any need for OpenSSH daemon or network loopback sockets.
"""
import os
import pwd
import grp
import logging
import asyncio
import subprocess
from typing import Optional

from dashboard.config import PAM_SERVICE

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Raised when Linux credentials fail authentication."""
    pass


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


def verify_linux_credentials(username: str, password: str) -> bool:
    """
    Verify user credentials directly on the Linux host.
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


async def authenticate_user(username: str, password: str) -> dict:
    """
    Authenticate user using native Linux PAM/shadow and return user profile.
    Raises AuthError on invalid credentials.
    """
    user_info = get_local_user_info(username)
    is_valid = await asyncio.to_thread(verify_linux_credentials, username, password)
    if not is_valid:
        raise AuthError("Invalid username or password.")
    return user_info


async def run_command_async(cmd: list[str] | str, timeout: int = 30) -> tuple[int, str, str]:
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


async def run_user_service_async(uid: int, cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """
    Execute systemctl --user command ensuring proper XDG and D-Bus runtime variables.
    Prevents 'Failed to connect to bus: No such file or directory' errors.
    """
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


async def verify_sudo_password(password: str) -> tuple[bool, str]:
    """
    Validate user password with sudo and refresh Linux sudo timestamp ticket.
    Runs `sudo -S -p '' -v` piping password via stdin.
    """
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


async def run_sudo_async(
    cmd: list[str],
    password: Optional[str] = None,
    timeout: int = 30,
) -> tuple[int, str, str]:
    """
    Execute a privileged command with sudo.
    If password is provided, pipes it to `sudo -S`.
    If password is None, uses `sudo -n` (non-interactive) relying on active elevation ticket or NOPASSWD.
    """
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


async def drop_sudo_ticket() -> None:
    """Revoke sudo timestamp ticket (`sudo -k`)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "sudo", "-k",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
    except Exception:
        pass
