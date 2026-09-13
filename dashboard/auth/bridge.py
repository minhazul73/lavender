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
    1. Direct shadow verification (if readable / shadow group)
    2. PAM authentication (login, base-auth, other, system-auth)
    3. Sudo validation (sudo -k followed by sudo -S -p '' -v)
    4. Doas validation (common on Alpine / postmarketOS)
    """
    if not password:
        return False

    # 1. Direct shadow verification (instant, works if user is in shadow group or root)
    try:
        import spwd
        import crypt
        sp = spwd.getspnam(username)
        if sp and sp.sp_pwdp:
            if crypt.crypt(password, sp.sp_pwdp) == sp.sp_pwdp:
                logger.info("Direct shadow authentication successful for user %s", username)
                return True
    except Exception as exc:
        logger.debug("Direct shadow auth unavailable: %s", exc)

    # 2. PAM authentication
    try:
        import pam
        p = pam.pam()
        candidate_services = [PAM_SERVICE, "base-auth", "login", "other", "common-auth", "system-auth", "sudo"]
        seen = set()
        for s in candidate_services:
            if s in seen:
                continue
            seen.add(s)
            # Only test services present in /etc/pam.d or 'other'
            if os.path.isdir("/etc/pam.d") and not os.path.isfile(f"/etc/pam.d/{s}") and s != "other":
                continue
            try:
                if p.authenticate(username, password, service=s):
                    logger.info("PAM authentication successful for user %s via service '%s'", username, s)
                    return True
                logger.debug("PAM service '%s' check returned %s: %s", s, p.code, p.reason)
            except Exception as e:
                logger.debug("PAM service '%s' exception: %s", s, e)
    except Exception as exc:
        logger.debug("PAM library auth failed or unavailable: %s", exc)

    # 3. Sudo validation (invalidate cache first, then validate with password)
    try:
        subprocess.run(["sudo", "-k"], capture_output=True, timeout=2)
        proc = subprocess.run(
            ["sudo", "-S", "-p", "", "-v"],
            input=f"{password}\n",
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0:
            logger.info("Sudo validation successful for user %s", username)
            return True
        logger.warning(
            "Sudo auth check failed for user %s (code %d): %s",
            username, proc.returncode, proc.stderr.strip()
        )
    except Exception as exc:
        logger.warning("Sudo auth check exception for %s: %s", username, exc)

    # 4. Doas validation (common on Alpine / postmarketOS)
    if os.path.isfile("/usr/bin/doas") or os.path.isfile("/bin/doas"):
        try:
            proc = subprocess.run(
                ["doas", "-C", "/etc/doas.conf", "true"],
                input=f"{password}\n",
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0:
                logger.info("Doas validation successful for user %s", username)
                return True
        except Exception:
            pass

    logger.warning("All credential verification methods failed for user '%s'", username)
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
