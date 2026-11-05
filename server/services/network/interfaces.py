"""
Network interface and IP address management.
"""
import json
import os
import re

from server.services.network.models import (
    InterfaceStats,
)
from server.services.network.utils import format_bytes, run_command


def get_gateways() -> list[dict]:
    """
    Get network default gateways and route details.

    Returns:
        List of gateway dictionaries with gateway IP, interface, protocol, metric, and prefsrc.
    """
    gateways = []
    code, out, _ = run_command(["ip", "-j", "route", "show", "default"], timeout=3)
    if code == 0 and out.strip().startswith("["):
        try:
            routes = json.loads(out)
            for r in routes:
                gw = r.get("gateway")
                dev = r.get("dev")
                if gw and dev:
                    gateways.append({
                        "gateway": gw,
                        "interface": dev,
                        "protocol": r.get("protocol", "static"),
                        "metric": r.get("metric", 0),
                        "prefsrc": r.get("prefsrc", "")
                    })
            if gateways:
                return gateways
        except Exception:
            pass

    code, out, _ = run_command(["ip", "route", "show", "default"], timeout=3)
    if code == 0:
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            m = re.match(r"default\s+via\s+(\S+)\s+dev\s+(\S+)", line)
            if m:
                gateways.append({
                    "gateway": m.group(1),
                    "interface": m.group(2),
                    "protocol": "dhcp" if "dhcp" in line else "static",
                    "metric": 0,
                    "prefsrc": ""
                })
    return gateways


def _determine_interface_category(name: str, link_type: str = None) -> str:
    """
    Determine the category of a network interface based on name and sysfs.

    Args:
        name: Interface name
        link_type: Link type from ip command (e.g., "loopback", "ether")

    Returns:
        Category string: loopback, wireless, cellular, bridge, virtual, or ethernet
    """
    is_loopback = (name == "lo" or link_type == "loopback")
    is_wireless = (
        os.path.exists(f"/sys/class/net/{name}/wireless")
        or os.path.exists(f"/sys/class/net/{name}/phy80211")
        or name.startswith(("wlan", "wlp", "wlo", "ra"))
    )
    is_bridge = (
        os.path.exists(f"/sys/class/net/{name}/bridge")
        or name == "docker0"
        or name.startswith("br-")
    )
    is_virtual = name.startswith(("veth", "tun", "tap", "wg", "tailscale", "dummy"))
    is_cellular = name.startswith(("wwan", "rmnet", "cdc-wdm"))

    if is_loopback:
        return "loopback"
    elif is_wireless:
        return "wireless"
    elif is_cellular:
        return "cellular"
    elif is_bridge:
        return "bridge"
    elif is_virtual:
        return "virtual"
    elif name.startswith(("eth", "enp", "eno", "ens")) or link_type == "ether":
        return "ethernet"
    return "ethernet"


def _read_interface_stats(name: str) -> InterfaceStats:
    """
    Read interface statistics from sysfs.

    Args:
        name: Interface name

    Returns:
        InterfaceStats dataclass with values from sysfs
    """
    stats = InterfaceStats()
    stat_path = f"/sys/class/net/{name}/statistics"
    if os.path.exists(stat_path):
        for k in ["rx_bytes", "tx_bytes", "rx_packets", "tx_packets", "rx_errors", "tx_errors"]:
            try:
                with open(os.path.join(stat_path, k)) as f:
                    setattr(stats, k, int(f.read().strip()))
            except Exception:
                pass
    return stats


def _read_interface_speed(name: str) -> str:
    """
    Read interface speed from sysfs.

    Args:
        name: Interface name

    Returns:
        Speed string (e.g., "1000 Mbps") or empty string if unavailable
    """
    try:
        with open(f"/sys/class/net/{name}/speed") as f:
            s_val = int(f.read().strip())
            if 0 < s_val < 1000000:
                return f"{s_val} Mbps"
    except Exception:
        pass
    return ""


def get_ip_addresses() -> list[dict]:
    """
    Get detailed network interfaces with accurate MTU, type, MAC, IP addresses,
    and RX/TX statistics.

    Returns:
        List of interface dictionaries sorted by priority
    """
    default_dev = None
    gateways = get_gateways()
    if gateways:
        default_dev = gateways[0].get("interface")

    interfaces = []

    # 1. Try ip -j addr show
    code, out, _ = run_command(["ip", "-j", "addr", "show"], timeout=5)
    if code == 0 and out.strip().startswith("["):
        try:
            raw_list = json.loads(out)
            for item in raw_list:
                name = item.get("ifname", "")
                if not name:
                    continue

                cat = _determine_interface_category(name, item.get("link_type"))

                mac = item.get("address")
                if mac in ("00:00:00:00:00:00", None) or name == "lo":
                    mac = None

                mtu = item.get("mtu", 0)
                if mtu == 0:
                    try:
                        with open(f"/sys/class/net/{name}/mtu") as f:
                            mtu = int(f.read().strip())
                    except Exception:
                        pass

                flags = item.get("flags", [])
                raw_state = item.get("operstate", "UNKNOWN").upper()
                if raw_state == "UNKNOWN" and "UP" in flags:
                    state = "UP"
                else:
                    state = raw_state

                ipv4_list = []
                ipv6_list = []
                flat_addresses = []

                for addr in item.get("addr_info", []):
                    local_ip = addr.get("local")
                    prefix = addr.get("prefixlen")
                    if not local_ip:
                        continue
                    cidr = f"{local_ip}/{prefix}" if prefix is not None else local_ip
                    flat_addresses.append(cidr)

                    if addr.get("family") == "inet":
                        ipv4_list.append({
                            "address": local_ip,
                            "cidr": cidr,
                            "broadcast": addr.get("broadcast"),
                            "scope": addr.get("scope", "global"),
                        })
                    elif addr.get("family") == "inet6":
                        ipv6_list.append({
                            "address": local_ip,
                            "cidr": cidr,
                            "scope": addr.get("scope", "link"),
                        })

                stats = _read_interface_stats(name)
                speed_str = _read_interface_speed(name)

                interfaces.append({
                    "name": name,
                    "type": cat,
                    "category": cat,
                    "state": state,
                    "is_up": ("UP" in flags and state != "DOWN"),
                    "is_default": (name == default_dev),
                    "mac": mac,
                    "mtu": mtu,
                    "speed": speed_str or None,
                    "flags": flags,
                    "addresses": flat_addresses,
                    "ipv4": ipv4_list,
                    "ipv6": ipv6_list,
                    "rx_bytes_fmt": format_bytes(stats.rx_bytes),
                    "tx_bytes_fmt": format_bytes(stats.tx_bytes),
                    "stats": {
                        "rx_bytes": stats.rx_bytes,
                        "tx_bytes": stats.tx_bytes,
                        "rx_packets": stats.rx_packets,
                        "tx_packets": stats.tx_packets,
                        "rx_errors": stats.rx_errors,
                        "tx_errors": stats.tx_errors,
                    },
                })
        except Exception:
            interfaces = []

    # 2. Fallback to /sys/class/net and ip -o addr
    if not interfaces and os.path.exists("/sys/class/net"):
        for name in os.listdir("/sys/class/net"):
            cat = _determine_interface_category(name)

            mtu = 0
            try:
                with open(f"/sys/class/net/{name}/mtu") as f:
                    mtu = int(f.read().strip())
            except Exception:
                pass

            state = "DOWN"
            try:
                with open(f"/sys/class/net/{name}/operstate") as f:
                    state = f.read().strip().upper()
            except Exception:
                pass

            mac = None
            try:
                with open(f"/sys/class/net/{name}/address") as f:
                    m = f.read().strip()
                    if m and m != "00:00:00:00:00:00" and name != "lo":
                        mac = m
            except Exception:
                pass

            stats = _read_interface_stats(name)

            interfaces.append({
                "name": name,
                "type": cat,
                "category": cat,
                "state": state,
                "is_up": (state == "UP"),
                "is_default": (name == default_dev),
                "mac": mac,
                "mtu": mtu,
                "speed": None,
                "flags": ["UP"] if state == "UP" else [],
                "addresses": [],
                "ipv4": [],
                "ipv6": [],
                "rx_bytes_fmt": format_bytes(stats.rx_bytes),
                "tx_bytes_fmt": format_bytes(stats.tx_bytes),
                "stats": {
                    "rx_bytes": stats.rx_bytes,
                    "tx_bytes": stats.tx_bytes,
                    "rx_packets": stats.rx_packets,
                    "tx_packets": stats.tx_packets,
                    "rx_errors": stats.rx_errors,
                    "tx_errors": stats.tx_errors,
                },
            })

        code, out, _ = run_command(["ip", "-o", "addr", "show"], timeout=5)
        if code == 0:
            iface_map = {i["name"]: i for i in interfaces}
            for line in out.splitlines():
                m = re.match(r"^\d+:\s+(\S+)\s+(inet6?)\s+(\S+)", line.strip())
                if m:
                    iface_name = m.group(1)
                    family = m.group(2)
                    ip_cidr = m.group(3)
                    ip_clean = ip_cidr.split("/")[0]
                    if iface_name in iface_map:
                        cur = iface_map[iface_name]
                        if ip_cidr not in cur["addresses"]:
                            cur["addresses"].append(ip_cidr)
                        if family == "inet":
                            cur["ipv4"].append({"address": ip_clean, "cidr": ip_cidr, "scope": "global"})
                        else:
                            cur["ipv6"].append({"address": ip_clean, "cidr": ip_cidr, "scope": "link"})

    def sort_key(iface):
        score = 100
        name = iface.get("name", "")
        is_tailscale = name.startswith("tailscale")
        if is_tailscale:
            score = 80
        elif iface.get("is_default"):
            score = 10
        elif iface.get("category") == "wireless":
            score = 20
        elif iface.get("category") == "ethernet" and iface.get("is_up"):
            score = 25
        elif iface.get("category") == "ethernet":
            score = 30
        elif iface.get("category") == "loopback":
            score = 40
        elif iface.get("category") == "bridge":
            score = 60
        elif iface.get("category") == "virtual":
            score = 70
        return (score, iface["name"])

    interfaces.sort(key=sort_key)
    return interfaces
