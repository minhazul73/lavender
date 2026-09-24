"""
Lavender API subpackage.
Exports domain routers for device, system, network, packages, users, power, storage, auth, and live monitoring.
"""
from server.api import auth, device, live, network, packages, power, storage, system, users

__all__ = [
    "auth",
    "device",
    "live",
    "network",
    "packages",
    "power",
    "storage",
    "system",
    "users",
]
