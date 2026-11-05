"""
Network and WiFi management for Lavender dashboard.
Supports postmarketOS (Alpine / busybox / wpa_cli), Debian/Ubuntu (nmcli / iwconfig / iw),
and standard Linux kernel sysfs / procfs.
"""

__all__ = [
    "get_network_summary",
    "ping_test",
    "dns_lookup",
    "get_dns_info",
    "get_gateways",
    "get_ip_addresses",
    "run_command",
    "get_wifi_info",
    "scan_wifi_networks",
]

from server.services.network.diagnostics import (
    get_network_summary,
    ping_test,
)
from server.services.network.dns import (
    dns_lookup,
    get_dns_info,
)
from server.services.network.interfaces import (
    get_gateways,
    get_ip_addresses,
)
from server.services.network.utils import (
    run_command,
)
from server.services.network.wifi import (
    get_wifi_info,
    scan_wifi_networks,
)
