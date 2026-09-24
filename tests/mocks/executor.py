from typing import Callable, Optional, Union
from server.core.executor import CommandResult


class MockCommandExecutor:
    """Configurable mock executor for subprocess testing."""

    def __init__(self):
        self.calls: list[dict] = []
        self._exact_responses: dict[tuple[str, ...], CommandResult] = {}
        self._prefix_responses: list[tuple[tuple[str, ...], CommandResult]] = []
        self._default_result = CommandResult(0, "", "")

    def register(self, cmd: list[str], result: CommandResult) -> None:
        """Register an exact command match."""
        self._exact_responses[tuple(cmd)] = result

    def register_prefix(self, prefix: list[str], result: CommandResult) -> None:
        """Register a command prefix match."""
        self._prefix_responses.append((tuple(prefix), result))

    def set_default(self, result: CommandResult) -> None:
        """Set default response for unregistered commands."""
        self._default_result = result

    def _resolve(self, cmd: list[str]) -> CommandResult:
        cmd_tuple = tuple(cmd)
        if cmd_tuple in self._exact_responses:
            return self._exact_responses[cmd_tuple]
        for prefix, res in self._prefix_responses:
            if cmd_tuple[:len(prefix)] == prefix:
                return res
        return self._default_result

    async def run(
        self,
        cmd: list[str],
        timeout: float = 15.0,
        env_overrides: Optional[dict[str, str]] = None,
    ) -> CommandResult:
        self.calls.append({"type": "run", "cmd": cmd, "timeout": timeout, "env": env_overrides})
        return self._resolve(cmd)

    async def run_with_stdin(
        self,
        cmd: list[str],
        stdin_data: str,
        timeout: float = 15.0,
    ) -> CommandResult:
        self.calls.append({"type": "run_with_stdin", "cmd": cmd, "stdin": stdin_data, "timeout": timeout})
        return self._resolve(cmd)

    async def run_as_user(
        self,
        uid: int,
        cmd: list[str],
        timeout: float = 15.0,
    ) -> CommandResult:
        self.calls.append({"type": "run_as_user", "uid": uid, "cmd": cmd, "timeout": timeout})
        return self._resolve(cmd)

    def run_sync(
        self,
        cmd: list[str],
        timeout: float = 15.0,
        env_overrides: Optional[dict[str, str]] = None,
    ) -> CommandResult:
        self.calls.append({"type": "run_sync", "cmd": cmd, "timeout": timeout, "env": env_overrides})
        return self._resolve(cmd)
