import asyncio
import concurrent.futures
import os
from typing import NamedTuple, Protocol

from server.core.command_validator import (
    HOST_RE,
    INVALID_CMD_SPEC,
    SAFE_EXECUTABLES,
    SHORT_OPTS_WITH_VAL,
    SUDO_OPTS_WITH_ARG,
    SUDO_STANDALONE_FLAGS,
    SUDO_VAL_PREFIXES,
    TRUSTED_PATH_DIRS,
    UNIT_RE,
    parse_sudo_command,
    validate_command,
    validate_executable,
)

_INVALID_CMD_SPEC = INVALID_CMD_SPEC


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
        self,
        cmd: list[str],
        timeout_sec: float = 15.0,
        env_overrides: dict[str, str] | None = None,
        **kwargs: float,
    ) -> CommandResult:
        """Run a command and capture output."""
        ...

    async def run_with_stdin(
        self,
        cmd: list[str],
        stdin_data: str,
        timeout_sec: float = 15.0,
        **kwargs: float,
    ) -> CommandResult:
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

    _SAFE_EXECUTABLES = SAFE_EXECUTABLES
    _TRUSTED_PATH_DIRS = TRUSTED_PATH_DIRS
    _SUDO_OPTS_WITH_ARG = SUDO_OPTS_WITH_ARG
    _SHORT_OPTS_WITH_VAL = SHORT_OPTS_WITH_VAL
    _SUDO_VAL_PREFIXES = SUDO_VAL_PREFIXES
    _SUDO_STANDALONE_FLAGS = SUDO_STANDALONE_FLAGS
    _HOST_RE = HOST_RE
    _UNIT_RE = UNIT_RE

    def _validate_executable(self, exe_token: str) -> str | None:
        return validate_executable(exe_token)

    def _parse_sudo_command(self, cmd: list[str]) -> tuple[str | None, str | None]:
        return parse_sudo_command(cmd)

    def _validate_command(self, cmd: list[str]) -> str | None:
        return validate_command(cmd)

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
        timeout_sec: float = 15.0,
        env_overrides: dict[str, str] | None = None,
        **kwargs: float,
    ) -> CommandResult:
        timeout_val = float(kwargs.get("timeout", timeout_sec))
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
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_val)
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

    async def run_with_stdin(
        self,
        cmd: list[str],
        stdin_data: str,
        timeout_sec: float = 15.0,
        **kwargs: float,
    ) -> CommandResult:
        timeout_val = float(kwargs.get("timeout", timeout_sec))
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
                proc.communicate(input=stdin_data.encode()), timeout=timeout_val
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
