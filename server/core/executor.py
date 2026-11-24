import asyncio
import concurrent.futures
import os
import re
from typing import NamedTuple, Protocol

_INVALID_CMD_SPEC = "Invalid command specification"


async def _kill_proc(proc: asyncio.subprocess.Process | None) -> None:
    if proc:
        try:
            proc.kill()
            await proc.wait()
        except ProcessLookupError:
            pass


class CommandResult(NamedTuple):
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


class CommandExecutor(Protocol):
    """Mockable interface for all subprocess execution."""

    async def run(
        self, cmd: list[str], timeout: float = 15.0, env_overrides: dict[str, str] | None = None
    ) -> CommandResult:
        """Run a command and capture output."""
        ...

    async def run_with_stdin(self, cmd: list[str], stdin_data: str, timeout: float = 15.0) -> CommandResult:
        """Run a command with data piped to stdin (e.g., sudo -S, chpasswd)."""
        ...

    async def run_as_user(self, uid: int, cmd: list[str], timeout: float = 15.0) -> CommandResult:
        """Run command with user environment for systemd --user."""
        ...

    def run_sync(
        self, cmd: list[str], timeout: float = 15.0, env_overrides: dict[str, str] | None = None
    ) -> CommandResult:
        """Synchronous command execution helper for worker threads."""
        ...


class SystemCommandExecutor:
    """Production executor running real Linux subprocesses."""

    _SAFE_EXECUTABLES = frozenset([
        "echo", "cat", "sleep", "uname", "test", "id", "groups", "who", "last", "systemctl",
        "journalctl", "loginctl", "hostnamectl", "kill", "pkill", "ps", "sudo", "doas",
        "poweroff", "reboot", "shutdown", "lsblk", "chpasswd", "visudo", "ip", "iw",
        "iwconfig", "nmcli", "wpa_cli", "rfkill", "ping", "resolvectl", "systemd-resolve",
        "apk", "apt", "apt-cache", "apt-get", "dpkg", "dpkg-query", "pacman", "rpm",
        "dnf", "zypper", "flatpak", "snap", "checkupdates", "cpupower", "upower", "df",
        "du", "free", "find", "head", "tail", "grep", "awk", "sed", "cut", "tr", "sort",
        "uniq", "wc", "cp", "mv", "rm", "mkdir", "chmod", "usermod", "gpasswd", "addgroup",
        "delgroup", "umount",
    ])
    _TRUSTED_PATH_DIRS = frozenset(["/bin", "/usr/bin", "/sbin", "/usr/sbin", "/usr/local/bin", "/usr/local/sbin"])
    _SUDO_OPTS_WITH_ARG = frozenset([
        "-u", "--user", "-g", "--group", "-p", "--prompt", "-C", "--close-from", "-D",
        "--chdir", "-h", "--host", "-R", "--chroot", "-T", "--command-timeout", "-U", "--other-user", "-a",
    ])
    _SHORT_OPTS_WITH_VAL = frozenset("ugpCDhRTUa")
    _SUDO_VAL_PREFIXES = ("--user=", "--group=", "--prompt=", "--chdir=", "--host=", "--chroot=")
    _SUDO_STANDALONE_FLAGS = frozenset({"-v", "-k", "-K", "-l", "--validate", "--kill", "--reset-timestamp", "--list"})
    _HOST_RE = re.compile(r"^[a-zA-Z0-9.:_-]+$")
    _UNIT_RE = re.compile(r"^[a-zA-Z0-9_@.][a-zA-Z0-9_\-@.]*$")

    def _validate_executable(self, exe_token: str) -> str | None:
        if not exe_token:
            return _INVALID_CMD_SPEC
        dir_path = os.path.dirname(exe_token)
        if dir_path and dir_path not in self._TRUSTED_PATH_DIRS:
            return f"Executable path not trusted: {exe_token}"
        exe_name = os.path.basename(exe_token)
        if exe_name not in self._SAFE_EXECUTABLES:
            return f"Executable not allowed: {exe_name}"
        return None

    def _parse_sudo_command(self, cmd: list[str]) -> tuple[str | None, str | None]:
        i = 1
        n = len(cmd)
        while i < n:
            arg = cmd[i]
            if arg == "--":
                i += 1
                break
            if arg.startswith("--"):
                if any(arg.startswith(p) for p in self._SUDO_VAL_PREFIXES):
                    i += 1
                elif arg in self._SUDO_OPTS_WITH_ARG:
                    i += 2
                else:
                    i += 1
                continue
            if arg.startswith("-") and len(arg) > 1:
                consumed = False
                for j, ch in enumerate(arg[1:], start=1):
                    if ch in self._SHORT_OPTS_WITH_VAL:
                        i += 1 if j + 1 < len(arg) else 2
                        consumed = True
                        break
                if not consumed:
                    i += 1
                continue
            break

        if i < n:
            return cmd[i], None
        if any(c in self._SUDO_STANDALONE_FLAGS for c in cmd[1:]):
            return None, None
        return None, _INVALID_CMD_SPEC

    def _validate_command(self, cmd: list[str]) -> str | None:
        if not cmd:
            return _INVALID_CMD_SPEC
        err = self._validate_executable(cmd[0])
        if err:
            return err

        exe = os.path.basename(cmd[0])
        actual_exe = exe
        if exe in {"sudo", "doas"}:
            target_token, err = self._parse_sudo_command(cmd)
            if err:
                return err
            if target_token:
                sub_err = self._validate_executable(target_token)
                if sub_err:
                    return sub_err
                actual_exe = os.path.basename(target_token)

        if actual_exe == "ping":
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
        self, cmd: list[str], timeout: float = 15.0, env_overrides: dict[str, str] | None = None
    ) -> CommandResult:
        if not cmd or not isinstance(cmd, (list, tuple)) or not all(isinstance(c, str) for c in cmd):
            return CommandResult(-1, "", _INVALID_CMD_SPEC)
        validation_error = self._validate_command(list(cmd))
        if validation_error:
            return CommandResult(-1, "", validation_error)
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
            await _kill_proc(proc)
            return CommandResult(-1, "", "Command timed out", timed_out=True)
        except FileNotFoundError:
            return CommandResult(127, "", f"Executable not found: {cmd[0] if cmd else ''}")
        except Exception as e:
            return CommandResult(-1, "", str(e))

    async def run_with_stdin(self, cmd: list[str], stdin_data: str, timeout: float = 15.0) -> CommandResult:
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
            await _kill_proc(proc)
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
        self, cmd: list[str], timeout: float = 15.0, env_overrides: dict[str, str] | None = None
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
            return CommandResult(-1, "", _INVALID_CMD_SPEC)
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
