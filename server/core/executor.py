import asyncio
import os
import subprocess
from typing import NamedTuple, Optional, Protocol


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
        env_overrides: Optional[dict[str, str]] = None,
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
        env_overrides: Optional[dict[str, str]] = None,
    ) -> CommandResult:
        """Synchronous command execution helper for worker threads."""
        ...


class SystemCommandExecutor:
    """Production executor running real Linux subprocesses."""

    def _build_env(self, uid: Optional[int] = None, overrides: Optional[dict[str, str]] = None) -> dict[str, str]:
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
        env_overrides: Optional[dict[str, str]] = None,
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
        except asyncio.TimeoutError:
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
        except asyncio.TimeoutError:
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
        env_overrides: Optional[dict[str, str]] = None,
    ) -> CommandResult:
        env = self._build_env(overrides=env_overrides)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
            return CommandResult(
                returncode=result.returncode,
                stdout=result.stdout.strip(),
                stderr=result.stderr.strip(),
                timed_out=False,
            )
        except subprocess.TimeoutExpired:
            return CommandResult(-1, "", "Command timed out", timed_out=True)
        except FileNotFoundError:
            return CommandResult(127, "", f"Executable not found: {cmd[0] if cmd else ''}")
        except Exception as e:
            return CommandResult(-1, "", str(e))


# Dependency-injection point (swappable in tests)
_executor: CommandExecutor = SystemCommandExecutor()


def get_executor() -> CommandExecutor:
    return _executor


def set_executor(executor: CommandExecutor) -> None:
    global _executor
    _executor = executor
