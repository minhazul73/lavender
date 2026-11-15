"""
Subprocess execution utilities.
"""
from server.core.executor import get_executor


def run_command(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Execute command via system executor synchronously."""
    res = get_executor().run_sync(cmd, timeout=float(timeout))
    return res.returncode, res.stdout, res.stderr


def run_sudo_command(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Execute privileged sudo command via system executor synchronously."""
    full_cmd = ["sudo"] + cmd if cmd and cmd[0] == "-n" else ["sudo", "-n"] + cmd
    return run_command(full_cmd, timeout)
