"""
WiFi information and scanning.
"""
import os
import re

from server.services.network.models import WiFiInfo, WiFiNetwork
from server.services.network.utils import run_command
from server.utils.cmd import which


def _find_wifi_interfaces() -> list[str]:
    """
    Discover WiFi interfaces via sysfs and naming conventions.

    Returns:
        List of WiFi interface names
    """
    wifi_ifaces = []
    net_path = "/sys/class/net"
    if os.path.exists(net_path):
        for iface in os.listdir(net_path):
            if (
                os.path.exists(os.path.join(net_path, iface, "wireless"))
                or os.path.exists(os.path.join(net_path, iface, "phy80211"))
                or iface.startswith(("wlan", "wlp", "wlo", "ra"))
            ):
                wifi_ifaces.append(iface)
    return wifi_ifaces


def _parse_nmcli_wifi_line(line: str) -> WiFiNetwork | None:
    """
    Parse a single nmcli WiFi line into a WiFiNetwork dataclass.

    Args:
        line: Raw nmcli output line

    Returns:
        WiFiNetwork or None if parsing failed
    """
    parts = re.split(r"(?<!\\):", line)
    if len(parts) < 8:
        return None

    is_active = (parts[0].strip().lower() == "yes")
    raw_ssid = parts[1].replace(r"\:", ":").strip()
    raw_bssid = parts[2].replace(r"\:", ":").strip()
    mode = parts[3].strip()
    chan = parts[4].strip()
    freq = parts[5].strip()
    rate = parts[6].strip()
    sig = parts[7].strip()
    sec = parts[8].strip() if len(parts) > 8 else ""

    sig_num = int(sig) if sig.isdigit() else 0

    return WiFiNetwork(
        ssid=raw_ssid or "<Hidden SSID>",
        bssid=raw_bssid,
        mode=mode,
        channel=chan,
        frequency=freq,
        rate=rate,
        signal=sig_num,
        security=sec or "Open",
        is_current=is_active,
    )


def _try_nmcli(primary_iface: str, wifi_data: WiFiInfo) -> None:
    """
    Try to gather WiFi info via nmcli. Updates wifi_data in place.

    Args:
        primary_iface: Primary WiFi interface name
        wifi_data: WiFiInfo dataclass to populate
    """
    if not which("nmcli"):
        return

    try:
        code, out, _ = run_command([
            "nmcli", "-t", "-f",
            "active,ssid,bssid,mode,chan,freq,rate,signal,security",
            "dev", "wifi", "list", "--rescan", "no"
        ], timeout=4)
        if code == 0 and out:
            nearby = []
            for line in out.splitlines():
                net = _parse_nmcli_wifi_line(line)
                if net is None:
                    continue
                nearby.append(net)

                if net.is_current:
                    wifi_data.connected = True
                    wifi_data.ssid = net.ssid
                    wifi_data.bssid = net.bssid
                    wifi_data.channel = net.channel
                    wifi_data.frequency = net.frequency
                    wifi_data.bitrate = net.rate
                    wifi_data.signal_percent = net.signal
                    wifi_data.security = net.security
                    wifi_data.mode = net.mode
                    wifi_data.source = "nmcli"
            wifi_data.nearby = nearby[:20]
    except Exception:
        pass


def _try_iwconfig(primary_iface: str, wifi_data: WiFiInfo) -> None:
    """
    Try to gather WiFi info via iwconfig. Updates wifi_data in place.

    Args:
        primary_iface: Primary WiFi interface name
        wifi_data: WiFiInfo dataclass to populate
    """
    if not which("iwconfig"):
        return

    try:
        code, out, _ = run_command(["iwconfig", primary_iface], timeout=3)
        if code == 0 and out:
            essid_m = re.search(r'ESSID:"([^"]+)"', out)
            if essid_m:
                wifi_data.ssid = essid_m.group(1)
                wifi_data.connected = True

            ap_m = re.search(r"Access Point:\s*([0-9A-Fa-f:]{17})", out)
            if ap_m:
                wifi_data.bssid = ap_m.group(1)
                wifi_data.connected = True

            rate_m = re.search(r"Bit Rate[=:]([\d.]+ \S+)", out)
            if rate_m:
                wifi_data.bitrate = rate_m.group(1)

            freq_m = re.search(r"Frequency[=:]([\d.]+ \S+)", out)
            if freq_m:
                wifi_data.frequency = freq_m.group(1)

            tx_m = re.search(r"Tx-Power[=:]([\d.]+ \S+)", out)
            if tx_m:
                wifi_data.tx_power = tx_m.group(1)

            qual_m = re.search(r"Link Quality=([0-9/]+)", out)
            if qual_m:
                wifi_data.quality = qual_m.group(1)
                try:
                    q_parts = qual_m.group(1).split("/")
                    if len(q_parts) == 2 and float(q_parts[1]) > 0:
                        q_percent = int((float(q_parts[0]) / float(q_parts[1])) * 100)
                        if wifi_data.signal_percent is None:
                            wifi_data.signal_percent = min(100, max(0, q_percent))
                except Exception:
                    pass

            sig_m = re.search(r"Signal level[=:](-?[\d.]+ \S+)", out)
            if sig_m:
                wifi_data.signal_dbm = sig_m.group(1)

            mode_m = re.search(r"Mode:(\S+)", out)
            if mode_m and not wifi_data.mode:
                wifi_data.mode = mode_m.group(1)

            if not wifi_data.source:
                wifi_data.source = "iwconfig"
    except Exception:
        pass


def _try_iw(primary_iface: str, wifi_data: WiFiInfo) -> None:
    """
    Try to gather WiFi info via iw. Updates wifi_data in place.

    Args:
        primary_iface: Primary WiFi interface name
        wifi_data: WiFiInfo dataclass to populate
    """
    if not which("iw") or (wifi_data.connected and wifi_data.signal_percent is not None):
        return

    try:
        code, out, _ = run_command(["iw", "dev", primary_iface, "link"], timeout=3)
        if code == 0 and "Connected to" in out:
            wifi_data.connected = True
            bssid_m = re.search(r"Connected to ([0-9a-f:]{17})", out, re.IGNORECASE)
            if bssid_m and not wifi_data.bssid:
                wifi_data.bssid = bssid_m.group(1).upper()
            ssid_m = re.search(r"SSID:\s*(.+)", out)
            if ssid_m and not wifi_data.ssid:
                wifi_data.ssid = ssid_m.group(1).strip()
            freq_m = re.search(r"freq:\s*(\d+)", out)
            if freq_m and not wifi_data.frequency:
                freq_val = int(freq_m.group(1))
                wifi_data.frequency = f"{freq_val / 1000.0:.3f} GHz"
            sig_m = re.search(r"signal:\s*(-?[\d.]+)\s*dBm", out)
            if sig_m and not wifi_data.signal_dbm:
                dbm_val = float(sig_m.group(1))
                wifi_data.signal_dbm = f"{dbm_val} dBm"
                if wifi_data.signal_percent is None:
                    pct = int(max(0, min(100, 2 * (dbm_val + 100))))
                    wifi_data.signal_percent = pct
            bit_m = re.search(r"tx bitrate:\s*([^\n]+)", out)
            if bit_m and not wifi_data.bitrate:
                wifi_data.bitrate = bit_m.group(1).strip()
            if not wifi_data.source:
                wifi_data.source = "iw"
    except Exception:
        pass


def _try_proc_wireless(primary_iface: str, wifi_data: WiFiInfo) -> None:
    """
    Try to gather WiFi info from /proc/net/wireless. Updates wifi_data in place.

    Args:
        primary_iface: Primary WiFi interface name
        wifi_data: WiFiInfo dataclass to populate
    """
    if not os.path.exists("/proc/net/wireless"):
        return

    try:
        with open("/proc/net/wireless") as f:
            for line in f:
                if primary_iface in line:
                    p = line.split()
                    if len(p) >= 4:
                        qual = p[2].rstrip(".")
                        level = p[3].rstrip(".")
                        if not wifi_data.quality and qual:
                            wifi_data.quality = qual
                        if not wifi_data.signal_dbm and level:
                            wifi_data.signal_dbm = f"{level} dBm"
                            if wifi_data.signal_percent is None:
                                try:
                                    dbm = float(level)
                                    pct = int(max(0, min(100, 2 * (dbm + 100))))
                                    wifi_data.signal_percent = pct
                                except Exception:
                                    pass
                        wifi_data.connected = True
    except Exception:
        pass


def _check_rfkill() -> bool:
    """
    Check if WiFi is blocked by rfkill.

    Returns:
        True if WiFi is soft-blocked, False otherwise
    """
    if not which("rfkill"):
        return False
    try:
        code, out, _ = run_command(["rfkill", "list", "wifi"], timeout=2)
        if code == 0 and "Soft blocked: yes" in out:
            return True
    except Exception:
        pass
    return False


def get_wifi_info() -> dict:
    """
    Get comprehensive WiFi information across nmcli, iwconfig, iw, wpa_cli,
    and Linux sysfs/procfs.

    Returns:
        Dictionary with WiFi connection details and nearby networks
    """
    wifi_data = WiFiInfo()

    wifi_ifaces = _find_wifi_interfaces()

    if wifi_ifaces:
        wifi_data.has_hardware = True
        wifi_data.available_interfaces = wifi_ifaces
        wifi_data.interface = wifi_ifaces[0]
    else:
        return {
            "has_hardware": False,
            "connected": False,
            "message": "No wireless network interfaces detected on this device.",
            "available_interfaces": [],
            "nearby": [],
        }

    primary_iface = wifi_data.interface

    # 1. Try nmcli
    _try_nmcli(primary_iface, wifi_data)

    # 2. Try iwconfig
    _try_iwconfig(primary_iface, wifi_data)

    # 3. Try iw
    _try_iw(primary_iface, wifi_data)

    # 4. Try /proc/net/wireless
    _try_proc_wireless(primary_iface, wifi_data)

    # 5. Check rfkill
    wifi_data.rfkill_blocked = _check_rfkill()

    return wifi_data.to_dict()


def scan_wifi_networks() -> list[dict]:
    """
    Trigger an active scan for nearby WiFi networks.

    Returns:
        List of nearby WiFi network dictionaries
    """
    if not which("nmcli"):
        return []

    try:
        run_command(["nmcli", "dev", "wifi", "rescan"], timeout=6)
        code, out, _ = run_command([
            "nmcli", "-t", "-f",
            "active,ssid,bssid,mode,chan,freq,rate,signal,security",
            "dev", "wifi", "list"
        ], timeout=5)
        if code == 0 and out:
            results = []
            for line in out.splitlines():
                net = _parse_nmcli_wifi_line(line)
                if net is not None:
                    results.append(net.to_dict())
            return results[:25]
    except Exception:
        pass
    return []
