"""
Network validation utilities.
"""
import ipaddress
import re

HOSTNAME_REGEX = re.compile(
    r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][a-zA-Z0-9\-]*[A-Za-z0-9])$"
)


def is_valid_ipv4(address: str) -> bool:
    """Check if address is valid IPv4."""
    try:
        ipaddress.IPv4Address(address.strip())
        return True
    except (ValueError, ipaddress.AddressValueError):
        return False


def is_valid_ipv6(address: str) -> bool:
    """Check if address is valid IPv6."""
    try:
        ipaddress.IPv6Address(address.strip())
        return True
    except (ValueError, ipaddress.AddressValueError):
        return False


def is_valid_hostname(hostname: str) -> bool:
    """Check if string is a valid RFC 1123 hostname."""
    h = hostname.strip()
    if not h or len(h) > 255:
        return False
    if h.endswith("."):
        h = h[:-1]
    return bool(HOSTNAME_REGEX.match(h))
