"""
Utility functions for network service.
"""

from server.core.executor import get_executor


def run_command(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """
    Execute a shell command and return the result.

    Args:
        cmd: Command to execute as list of strings
        timeout: Maximum execution time in seconds

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    res = get_executor().run_sync(cmd, timeout=float(timeout))
    return res.returncode, res.stdout, res.stderr


def format_bytes(bytes_count: int) -> str:
    """
    Format bytes into human readable string (KB, MB, GB).

    Args:
        bytes_count: Number of bytes to format

    Returns:
        Formatted string with unit
    """
    if bytes_count <= 0:
        return "0 B"
    val = float(bytes_count)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if val < 1024.0:
            return f"{val:.1f} {unit}" if unit != "B" else f"{int(val)} B"
        val /= 1024.0
    return f"{val:.1f} PB"


def get_known_dns_provider(ip: str) -> str:
    """
    Identify well-known DNS provider names from IP.

    Args:
        ip: IP address to identify

    Returns:
        Provider name or "Unknown"
    """
    if not ip:
        return "Unknown"
    if ip.startswith("127.") or ip == "::1":
        return "Local Stub Resolver"
    if ip in ("1.1.1.1", "1.0.0.1", "2606:4700:4700::1111", "2606:4700:4700::1001"):
        return "Cloudflare DNS"
    if ip in ("8.8.8.8", "8.8.4.4", "2001:4860:4860::8888", "2001:4860:4860::8844"):
        return "Google Public DNS"
    if ip in ("9.9.9.9", "149.112.112.112", "2620:fe::fe", "2620:fe::9"):
        return "Quad9"
    if ip in ("208.67.222.222", "208.67.220.220"):
        return "OpenDNS"
    if ip in ("94.140.14.14", "94.140.15.15"):
        return "AdGuard DNS"
    if ip.startswith(("192.168.", "10.", "172.16.", "172.17.", "172.18.", "172.19.", "172.2", "172.30.", "172.31.")):
        return "Local Router / Gateway"
    return "ISP / Custom DNS"
