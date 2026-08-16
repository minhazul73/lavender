"""
Network and WiFi management.
"""
import subprocess
import re
import os

from dashboard.dependencies import run_command, run_sudo_command, which


def get_ip_addresses() -> list[dict]:
    """
    Run ip -o addr and parse interface information.
    ip -o addr output format (one line per address):
      1: lo    inet 127.0.0.1/8 scope host lo\       valid_lft forever preferred_lft forever
      3: wlan0    inet 192.168.68.250/22 brd 192.168.71.255 scope global dynamic noprefixroute wlan0\       ...
    Each line is one address. No separate <FLAGS> mtu block in -o mode.
    We track interfaces by index number, collect inet/inet6 addresses, and
    determine type/state from the scope field.
    """
    code, out, err = run_command(["ip", "-o", "addr", "show"], timeout=10)
    if code != 0:
        return [{"error": err}]

    # idx -> interface data
    ifaces = {}

    for line in out.split("\n"):
        line = line.strip()
        if not line:
            continue

        # Every line starts with: N: iface_name ...
        m = re.match(r"^(\d+):\s+(\S+)\s+", line)
        if not m:
            continue

        idx = int(m.group(1))
        name = m.group(2)

        # Create interface entry on first sighting
        if idx not in ifaces:
            ifaces[idx] = {
                "name": name,
                "type": "ethernet",
                "state": "DOWN",
                "flags": [],
                "mtu": 0,
                "addresses": [],
            }

        # Collect IPv4 address
        addr4 = re.search(r"inet\s+(\S+)", line)
        if addr4:
            ifaces[idx]["addresses"].append(addr4.group(1))
            # Scope determines type + state
            if "scope host" in line:
                ifaces[idx]["type"] = "loopback"
                ifaces[idx]["state"] = "UP"
                ifaces[idx]["flags"] = ["UP"]
            elif "scope link" in line:
                ifaces[idx]["state"] = "UP"
                ifaces[idx]["flags"] = ["UP", "LOWER_UP"]
            elif "scope global" in line:
                ifaces[idx]["state"] = "UP"
                ifaces[idx]["flags"] = ["UP", "BROADCAST", "MULTICAST", "LOWER_UP"]

        # Collect IPv6 address
        addr6 = re.search(r"inet6\s+(\S+)", line)
        if addr6:
            ifaces[idx]["addresses"].append(addr6.group(1))
            if "scope link" in line:
                ifaces[idx]["state"] = "UP"
                ifaces[idx]["flags"] = ["UP", "LOWER_UP"]
            elif "scope global" in line:
                ifaces[idx]["state"] = "UP"
                ifaces[idx]["flags"] = ["UP", "BROADCAST", "MULTICAST", "LOWER_UP"]

    # Convert to sorted list
    result = []
    for idx in sorted(ifaces.keys()):
        iface = ifaces[idx]
        # loopback if name is lo or type was set to loopback by scope
        if iface["name"] == "lo" or iface["type"] == "loopback":
            iface["type"] = "loopback"
        result.append(iface)
    return result


def get_wifi_info() -> list[dict]:
    """
    Get WiFi interface information using iw or iwinfo.
    """
    results = []
    
    # Try iw first
    iw_path = which("iw")
    if iw_path:
        code, out, err = run_command(["iw", "dev"], timeout=10)
        if code == 0:
            # Parse interfaces
            current_iface = None
            for line in out.split("\n"):
                line = line.strip()
                if line.startswith("Interface"):
                    current_iface = line.split()[1]
                    results.append({
                        "interface": current_iface,
                        "method": "iw",
                        "ssid": "",
                        "signal": "",
                        "quality": "",
                        "channel": "",
                        "tx_rate": "",
                    })
                elif current_iface and "ssid" in line.lower():
                    # Will need iw scan for full info - skip for lightweight
                    pass
    
    # Try iwinfo if available
    iwinfo_path = which("iwinfo")
    if iwinfo_path:
        # Try to get info for each wireless interface
        for iface in results:
            code, out, err = run_command(["iwinfo", iface["interface"], "info"], timeout=10)
            if code == 0:
                for line in out.split("\n"):
                    if "SSID" in line:
                        m = re.search(r"SSID:\s*(.+)", line)
                        if m:
                            iface["ssid"] = m.group(1).strip()
                    if "Signal" in line or " dBm" in line:
                        m = re.search(r"([\d.-]+)\s*dBm", line)
                        if m:
                            iface["signal"] = m.group(1)
                    if "Frequency" in line:
                        m = re.search(r"Frequency:\s*([\d.]+)", line)
                        if m:
                            iface["channel"] = m.group(1)
    else:
        # iwinfo not available — try iw dev wlan0 link
        for iface_info in results:
            iface = iface_info["interface"]
            code, out, err = run_command(["iw", "dev", iface, "link"], timeout=10)
            if code == 0:
                for line in out.split("\n"):
                    if "SSID" in line:
                        m = re.search(r"SSID:\s*(.+)", line)
                        if m:
                            iface_info["ssid"] = m.group(1).strip()
                    if "signal:" in line:
                        m = re.search(r"signal:\s*([-\d.]+)", line)
                        if m:
                            iface_info["signal"] = m.group(1)
                    if "tx bitrate" in line:
                        m = re.search(r"tx bitrate:\s*([\d.]+)", line)
                        if m:
                            iface_info["tx_rate"] = m.group(1)
    
    return results if results else [{"note": "No WiFi interfaces found or iw not available"}]


def get_dns_servers() -> list[str]:
    """Get DNS servers from resolv.conf."""
    try:
        with open("/etc/resolv.conf", "r") as f:
            servers = []
            for line in f:
                line = line.strip()
                if line.startswith("nameserver"):
                    parts = line.split()
                    if len(parts) >= 2:
                        servers.append(parts[1])
            return servers
    except Exception:
        pass
    return []


def ping_test(target: str = "8.8.8.8", count: int = 3) -> dict:
    """
    Run ping test and return results.
    """
    code, out, err = run_command(["ping", "-c", str(count), "-W", "2", target], timeout=10 + count * 2)
    result = {
        "target": target,
        "success": code == 0,
        "output": out,
        "error": err,
        "avg_latency": None,
    }
    
    # Parse average latency
    m = re.search(r"rtt min/avg/max/mdev\s*=\s*[\d.]+/([\d.]+)/[\d.]+", out)
    if m:
        result["avg_latency"] = float(m.group(1))
    
    return result


def get_gateways() -> list[dict]:
    """Get network gateways/routes."""
    code, out, err = run_command(["ip", "route", "show", "default"], timeout=5)
    if code != 0:
        return [{"error": err}]
    
    gateways = []
    for line in out.split("\n"):
        line = line.strip()
        if not line:
            continue
        # default via 192.168.1.1 dev eth0
        m = re.match(r"default\s+via\s+(\S+)\s+dev\s+(\S+)", line)
        if m:
            gateways.append({
                "gateway": m.group(1),
                "interface": m.group(2),
            })
    return gateways
