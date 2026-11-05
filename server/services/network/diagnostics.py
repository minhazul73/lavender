"""
Network diagnostics: ping tests and summaries.
"""
import re

from server.services.network.models import NetworkSummary, PingResult
from server.services.network.utils import format_bytes, run_command


def ping_test(target: str = "8.8.8.8", count: int = 3) -> dict:
    """
    Run ping test supporting both standard iputils and busybox formats.

    Args:
        target: Target host/IP to ping
        count: Number of ping packets

    Returns:
        Dictionary containing ping statistics
    """
    target = target.strip() or "8.8.8.8"
    if not re.match(r"^[a-zA-Z0-9.:_-]+$", target):
        return {
            "target": target,
            "success": False,
            "error": "Invalid ping target characters",
            "output": "",
            "avg_latency": None,
        }
    count = max(1, min(count, 10))
    code, out, err = run_command(["ping", "-c", str(count), "-W", "2", "--", target], timeout=12 + count * 2)

    result = PingResult(
        target=target,
        success=False,
        output=out,
        error=err,
        transmitted=count,
    )

    stat_m = re.search(r"(\d+)\s+packets transmitted,\s+(\d+)\s+(?:packets\s+)?received.*?([\d.]+)%\s+packet loss", out, re.IGNORECASE)
    if stat_m:
        tx = int(stat_m.group(1))
        rx = int(stat_m.group(2))
        loss = float(stat_m.group(3))
        result.transmitted = tx
        result.received = rx
        result.packet_loss_percent = loss
        result.success = rx > 0
    elif "64 bytes from" in out or "bytes from" in out:
        result.received = len(re.findall(r"bytes from", out))
        result.success = True
        result.packet_loss_percent = max(0.0, ((count - result.received) / count) * 100.0)

    rtt_m = re.search(r"rtt\s+min/avg/max/mdev\s*=\s*([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)", out)
    if rtt_m:
        result.min_latency = float(rtt_m.group(1))
        result.avg_latency = float(rtt_m.group(2))
        result.max_latency = float(rtt_m.group(3))
        result.mdev_latency = float(rtt_m.group(4))
    else:
        bb_m = re.search(r"(?:round-trip|rtt)\s+min/avg/max\s*=\s*([\d.]+)/([\d.]+)/([\d.]+)", out)
        if bb_m:
            result.min_latency = float(bb_m.group(1))
            result.avg_latency = float(bb_m.group(2))
            result.max_latency = float(bb_m.group(3))

    return result.to_dict()


def get_network_summary() -> dict:
    """
    Produce a top-level summary of active network state:
    Primary IP, default gateway, active DNS, total traffic, and online status.
    """
    from server.services.network.dns import get_dns_info
    from server.services.network.interfaces import get_gateways, get_ip_addresses
    from server.services.network.wifi import get_wifi_info

    gateways = get_gateways()
    default_gw = gateways[0]["gateway"] if gateways else None
    default_dev = gateways[0]["interface"] if gateways else None

    ifaces = get_ip_addresses()
    primary_ip = None
    primary_mac = None
    primary_type = "None"
    total_rx = 0
    total_tx = 0

    for i in ifaces:
        if i["name"] != "lo":
            total_rx += i.get("stats", {}).get("rx_bytes", 0)
            total_tx += i.get("stats", {}).get("tx_bytes", 0)
        if default_dev and i["name"] == default_dev:
            primary_type = i["category"]
            primary_mac = i["mac"]
            if i["ipv4"]:
                primary_ip = i["ipv4"][0]["address"]
            elif i["ipv6"]:
                primary_ip = i["ipv6"][0]["address"]

    if not primary_ip:
        for i in ifaces:
            if i["name"] != "lo" and i["is_up"] and i["ipv4"]:
                primary_ip = i["ipv4"][0]["address"]
                primary_type = i["category"]
                primary_mac = i["mac"]
                if not default_dev:
                    default_dev = i["name"]
                break

    dns_info = get_dns_info()
    primary_dns = dns_info["servers"][0]["ip"] if dns_info["servers"] else None
    primary_dns_provider = dns_info["servers"][0]["provider"] if dns_info["servers"] else None
    wifi = get_wifi_info()

    is_online = bool(primary_ip and (default_gw or primary_dns))

    summary = NetworkSummary(
        is_online=is_online,
        primary_interface=default_dev,
        primary_type=primary_type,
        primary_ip=primary_ip,
        primary_mac=primary_mac,
        default_gateway=default_gw,
        primary_dns=primary_dns,
        primary_dns_provider=primary_dns_provider,
        total_rx_fmt=format_bytes(total_rx),
        total_tx_fmt=format_bytes(total_tx),
        wifi_connected=wifi.get("connected", False),
        wifi_ssid=wifi.get("ssid"),
        wifi_signal=wifi.get("signal_percent"),
    )
    return summary.to_dict()
