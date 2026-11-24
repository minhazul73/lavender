"""Command policy and validation helpers for safe subprocess execution."""
import os
import re

INVALID_CMD_SPEC = "Invalid command specification"

SAFE_EXECUTABLES = frozenset([
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

TRUSTED_PATH_DIRS = frozenset([
    "/bin", "/usr/bin", "/sbin", "/usr/sbin", "/usr/local/bin", "/usr/local/sbin",
])

SUDO_OPTS_WITH_ARG = frozenset([
    "-u", "--user", "-g", "--group", "-p", "--prompt", "-C", "--close-from", "-D",
    "--chdir", "-h", "--host", "-R", "--chroot", "-T", "--command-timeout", "-U", "--other-user", "-a",
])
SHORT_OPTS_WITH_VAL = frozenset("ugpCDhRTUa")
SUDO_VAL_PREFIXES = ("--user=", "--group=", "--prompt=", "--chdir=", "--host=", "--chroot=")
SUDO_STANDALONE_FLAGS = frozenset({"-v", "-k", "-K", "-l", "--validate", "--kill", "--reset-timestamp", "--list"})

HOST_RE = re.compile(r"^[a-zA-Z0-9.:_-]+$")
UNIT_RE = re.compile(r"^[a-zA-Z0-9_@.][a-zA-Z0-9_\-@.]*$")


def validate_executable(exe_token: str) -> str | None:
    """Validate that the executable is allowlisted and located in a trusted directory."""
    if not exe_token:
        return INVALID_CMD_SPEC
    dir_path = os.path.dirname(exe_token)
    if dir_path and dir_path not in TRUSTED_PATH_DIRS:
        return f"Executable path not trusted: {exe_token}"
    exe_name = os.path.basename(exe_token)
    if exe_name not in SAFE_EXECUTABLES:
        return f"Executable not allowed: {exe_name}"
    return None


def _consume_long_opt(arg: str) -> int:
    """Return number of arguments consumed by a long option."""
    if any(arg.startswith(p) for p in SUDO_VAL_PREFIXES):
        return 1
    if arg in SUDO_OPTS_WITH_ARG:
        return 2
    return 1


def _consume_short_opt(arg: str) -> int:
    """Return number of arguments consumed by a short option or cluster."""
    for j, ch in enumerate(arg[1:], start=1):
        if ch in SHORT_OPTS_WITH_VAL:
            return 1 if j + 1 < len(arg) else 2
    return 1


def parse_sudo_command(cmd: list[str]) -> tuple[str | None, str | None]:
    """Parse sudo/doas command options to extract the target command token.

    Returns:
        (target_token, error_message)
    """
    i = 1
    n = len(cmd)
    while i < n:
        arg = cmd[i]
        if arg == "--":
            i += 1
            break
        if arg.startswith("--"):
            i += _consume_long_opt(arg)
            continue
        if arg.startswith("-") and len(arg) > 1:
            i += _consume_short_opt(arg)
            continue
        break

    if i < n:
        return cmd[i], None
    if any(c in SUDO_STANDALONE_FLAGS for c in cmd[1:]):
        return None, None
    return None, INVALID_CMD_SPEC


def validate_command(cmd: list[str]) -> str | None:
    """Validate a command and its executable against policy."""
    if not cmd:
        return INVALID_CMD_SPEC
    err = validate_executable(cmd[0])
    if err:
        return err

    exe = os.path.basename(cmd[0])
    actual_exe = exe
    if exe in {"sudo", "doas"}:
        target_token, err = parse_sudo_command(cmd)
        if err:
            return err
        if target_token:
            sub_err = validate_executable(target_token)
            if sub_err:
                return sub_err
            actual_exe = os.path.basename(target_token)

    if actual_exe == "ping":
        target = cmd[-1]
        if not target or target.startswith("-") or not HOST_RE.match(target):
            return "Invalid ping target"

    return None
