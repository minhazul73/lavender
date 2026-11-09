import asyncio
import concurrent.futures
import os
import re
from typing import NamedTuple, Protocol


class CommandResult(NamedTuple):
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


class CommandExecutor(Protocol):
    """Mockable interface for all subprocess execution."""

    async def run(
        self,
        cmd: list[str],
        timeout: float = 15.0,
        env_overrides: dict[str, str] | None = None,
    ) -> CommandResult:
        """Run a command and capture output."""
        ...

    async def run_with_stdin(
        self,
        cmd: list[str],
        stdin_data: str,
        timeout: float = 15.0,
    ) -> CommandResult:
        """Run a command with data piped to stdin (e.g., sudo -S, chpasswd)."""
        ...

    async def run_as_user(
        self,
        uid: int,
        cmd: list[str],
        timeout: float = 15.0,
    ) -> CommandResult:
        """Run command with user environment for systemd --user."""
        ...

    def run_sync(
        self,
        cmd: list[str],
        timeout: float = 15.0,
        env_overrides: dict[str, str] | None = None,
    ) -> CommandResult:
        """Synchronous command execution helper for worker threads."""
        ...


class SystemCommandExecutor:
    """Production executor running real Linux subprocesses."""

    _SAFE_EXECUTABLES = frozenset([
        "echo", "cat", "sleep", "uname", "test", "id", "groups", "who", "last",
        "systemctl", "journalctl", "loginctl", "hostnamectl", "kill", "pkill", "ps",
        "sudo", "doas", "poweroff", "reboot", "shutdown",
        "ip", "iw", "iwconfig", "nmcli", "wpa_cli", "rfkill", "ping", "resolvectl", "systemd-resolve",
        "apk", "apt", "apt-cache", "apt-get", "dpkg", "dpkg-query", "pacman", "rpm", "dnf", "zypper", "flatpak", "snap",
        "cpupower", "upower",
        "df", "du", "free", "find", "head", "tail", "grep", "awk", "sed", "cut", "tr", "sort", "uniq", "wc",
        "cp", "mv", "rm", "mkdir", "chmod", "usermod", "gpasswd", "addgroup", "delgroup",
    ])
    _HOST_RE = re.compile(r"^[a-zA-Z0-9.:_-]+$")
    _UNIT_RE = re.compile(r"^[a-zA-Z0-9_@.][a-zA-Z0-9_\-@.]*$")

    def _validate_command(self, cmd: list[str]) -> str | None:
        if not cmd:
            return "Invalid command specification"
        exe = os.path.basename(cmd[0])
        if exe in {"sudo", "doas"}:
            sub = [c for c in cmd[1:] if not c.startswith("-")]
            if sub and os.path.basename(sub[0]) not in self._SAFE_EXECUTABLES:
                return f"Executable not allowed: {sub[0]}"
        elif exe not in self._SAFE_EXECUTABLES:
            return f"Executable not allowed: {exe}"

        if exe == "ping" or (len(cmd) > 2 and cmd[2] == "ping"):
            target = cmd[-1]
            if not target or target.startswith("-") or not self._HOST_RE.match(target):
                return "Invalid ping target"

        return None

    def _build_env(self, uid: int | None = None, overrides: dict[str, str] | None = None) -> dict[str, str]:
        env = os.environ.copy()
        effective_uid = uid if uid is not None else os.getuid()
        if "XDG_RUNTIME_DIR" not in env or uid is not None:
            env["XDG_RUNTIME_DIR"] = f"/run/user/{effective_uid}"
        if "DBUS_SESSION_BUS_ADDRESS" not in env or uid is not None:
            rd = env["XDG_RUNTIME_DIR"]
            env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={rd}/systemd/private"
        if overrides:
            env.update(overrides)
        return env

    async def run(
        self,
        cmd: list[str],
        timeout: float = 15.0,
        env_overrides: dict[str, str] | None = None,
    ) -> CommandResult:
        env = self._build_env(overrides=env_overrides)
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return CommandResult(
                returncode=proc.returncode if proc.returncode is not None else 0,
                stdout=stdout.decode("utf-8", errors="replace").strip(),
                stderr=stderr.decode("utf-8", errors="replace").strip(),
                timed_out=False,
            )
        except TimeoutError:
            if proc:
                try:
                    proc.kill()
                    await proc.wait()
                except ProcessLookupError:
                    pass
            return CommandResult(-1, "", "Command timed out", timed_out=True)
        except FileNotFoundError:
            return CommandResult(127, "", f"Executable not found: {cmd[0] if cmd else ''}")
        except Exception as e:
            return CommandResult(-1, "", str(e))

    async def run_with_stdin(
        self,
        cmd: list[str],
        stdin_data: str,
        timeout: float = 15.0,
    ) -> CommandResult:
        validation_error = self._validate_command(cmd)
        if validation_error:
            return CommandResult(-1, "", validation_error)
        env = self._build_env()
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=stdin_data.encode()), timeout=timeout
            )
            return CommandResult(
                returncode=proc.returncode if proc.returncode is not None else 0,
                stdout=stdout.decode("utf-8", errors="replace").strip(),
                stderr=stderr.decode("utf-8", errors="replace").strip(),
                timed_out=False,
            )
        except TimeoutError:
            if proc:
                try:
                    proc.kill()
                    await proc.wait()
                except ProcessLookupError:
                    pass
            return CommandResult(-1, "", "Command timed out", timed_out=True)
        except FileNotFoundError:
            return CommandResult(127, "", f"Executable not found: {cmd[0] if cmd else ''}")
        except Exception as e:
            return CommandResult(-1, "", str(e))

    async def run_as_user(
        self,
        uid: int,
        cmd: list[str],
        timeout: float = 15.0,
    ) -> CommandResult:
        env_overrides = {
            "XDG_RUNTIME_DIR": f"/run/user/{uid}",
            "DBUS_SESSION_BUS_ADDRESS": f"unix:path=/run/user/{uid}/systemd/private",
        }
        return await self.run(cmd, timeout=timeout, env_overrides=env_overrides)

    def run_sync(
        self,
        cmd: list[str],
        timeout: float = 15.0,
        env_overrides: dict[str, str] | None = None,
    ) -> CommandResult:
        """Run a command synchronously, reusing the module thread pool when an event loop is running.

        Args:
            cmd: Command arguments to execute.
            timeout: Subprocess timeout in seconds.
            env_overrides: Optional environment variable overrides.

        Returns:
            CommandResult containing returncode, stdout, and stderr.
        """
        if not cmd or not isinstance(cmd, (list, tuple)) or not all(isinstance(c, str) for c in cmd):
            return CommandResult(-1, "", "Invalid command specification")
        validation_error = self._validate_command(list(cmd))
        if validation_error:
            return CommandResult(-1, "", validation_error)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            return _get_sync_pool().submit(
                asyncio.run,
                self.run(cmd, timeout=timeout, env_overrides=env_overrides),
            ).result()
        return asyncio.run(self.run(cmd, timeout=timeout, env_overrides=env_overrides))


_sync_pool: concurrent.futures.ThreadPoolExecutor | None = None


def _get_sync_pool() -> concurrent.futures.ThreadPoolExecutor:
    """Return or lazily initialize the shared persistent thread pool executor for synchronous runs."""
    global _sync_pool
    if _sync_pool is None:
        _sync_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix="sync_executor",
        )
    return _sync_pool


# Dependency-injection point (swappable in tests)
_executor: CommandExecutor = SystemCommandExecutor()


def get_executor() -> CommandExecutor:
    return _executor


def set_executor(executor: CommandExecutor) -> None:
    global _executor
    _executor = executor
