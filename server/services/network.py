"""
Network and WiFi management for Lavender dashboard.
Supports postmarketOS (Alpine / busybox / wpa_cli), Debian/Ubuntu (nmcli / iwconfig / iw),
and standard Linux kernel sysfs / procfs.
"""
import os
import re
import socket
import subprocess
import time
from typing import Optional

from dashboard.dependencies import run_command, which


def format_bytes(bytes_count: int) -> str:
    """Format bytes into human readable string (KB, MB, GB)."""
    if bytes_count <= 0:
        return "0 B"
    val = float(bytes_count)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if val < 1024.0:
            return f"{val:.1f} {unit}" if unit != "B" else f"{int(val)} B"
        val /= 1024.0
    return f"{val:.1f} PB"


def get_known_dns_provider(ip: str) -> str:
    """Identify well-known DNS provider names from IP."""
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


def get_gateways() -> list[dict]:
    """Get network default gateways and route details."""
    gateways = []
    code, out, _ = run_command(["ip", "-j", "route", "show", "default"], timeout=3)
    if code == 0 and out.strip().startswith("["):
        try:
            import json
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


def get_ip_addresses() -> list[dict]:
    """
    Get detailed network interfaces with accurate MTU, type, MAC, IP addresses,
    and RX/TX statistics.
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
            import json
            raw_list = json.loads(out)
            for item in raw_list:
                name = item.get("ifname", "")
                if not name:
                    continue

                cat = "ethernet"
                is_loopback = (name == "lo" or item.get("link_type") == "loopback")
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
                is_virtual = name.startswith(("veth", "tun", "tap", "wg", "dummy"))
                is_cellular = name.startswith(("wwan", "rmnet", "cdc-wdm"))

                if is_loopback:
                    cat = "loopback"
                elif is_wireless:
                    cat = "wireless"
                elif is_cellular:
                    cat = "cellular"
                elif is_bridge:
                    cat = "bridge"
                elif is_virtual:
                    cat = "virtual"
                elif name.startswith(("eth", "enp", "eno", "ens")) or item.get("link_type") == "ether":
                    cat = "ethernet"

                mac = item.get("address")
                if mac in ("00:00:00:00:00:00", None) or is_loopback:
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

                stats = {
                    "rx_bytes": 0, "tx_bytes": 0,
                    "rx_packets": 0, "tx_packets": 0,
                    "rx_errors": 0, "tx_errors": 0,
                }
                stat_path = f"/sys/class/net/{name}/statistics"
                if os.path.exists(stat_path):
                    for k in stats.keys():
                        try:
                            with open(os.path.join(stat_path, k)) as f:
                                stats[k] = int(f.read().strip())
                        except Exception:
                            pass

                speed_str = None
                try:
                    with open(f"/sys/class/net/{name}/speed") as f:
                        s_val = int(f.read().strip())
                        if 0 < s_val < 1000000:
                            speed_str = f"{s_val} Mbps"
                except Exception:
                    pass

                interfaces.append({
                    "name": name,
                    "type": cat,
                    "category": cat,
                    "state": state,
                    "is_up": ("UP" in flags and state != "DOWN"),
                    "is_default": (name == default_dev),
                    "mac": mac,
                    "mtu": mtu,
                    "speed": speed_str,
                    "flags": flags,
                    "addresses": flat_addresses,
                    "ipv4": ipv4_list,
                    "ipv6": ipv6_list,
                    "rx_bytes_fmt": format_bytes(stats["rx_bytes"]),
                    "tx_bytes_fmt": format_bytes(stats["tx_bytes"]),
                    "stats": stats,
                })
        except Exception:
            interfaces = []

    # 2. Fallback to /sys/class/net and ip -o addr
    if not interfaces and os.path.exists("/sys/class/net"):
        for name in os.listdir("/sys/class/net"):
            is_loopback = (name == "lo")
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
            cat = "loopback" if is_loopback else ("wireless" if is_wireless else ("bridge" if is_bridge else "ethernet"))

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
                    if m and m != "00:00:00:00:00:00" and not is_loopback:
                        mac = m
            except Exception:
                pass

            stats = {"rx_bytes": 0, "tx_bytes": 0, "rx_packets": 0, "tx_packets": 0, "rx_errors": 0, "tx_errors": 0}
            stat_path = f"/sys/class/net/{name}/statistics"
            if os.path.exists(stat_path):
                for k in stats.keys():
                    try:
                        with open(os.path.join(stat_path, k)) as f:
                            stats[k] = int(f.read().strip())
                    except Exception:
                        pass

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
                "rx_bytes_fmt": format_bytes(stats["rx_bytes"]),
                "tx_bytes_fmt": format_bytes(stats["tx_bytes"]),
                "stats": stats,
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
        if iface.get("is_default"):
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


def get_wifi_info() -> dict:
    """
    Get comprehensive WiFi information across nmcli, iwconfig, iw, wpa_cli,
    and Linux sysfs/procfs.
    """
    wifi_data = {
        "has_hardware": False,
        "connected": False,
        "interface": None,
        "ssid": None,
        "bssid": None,
        "signal_percent": None,
        "signal_dbm": None,
        "quality": None,
        "frequency": None,
        "channel": None,
        "bitrate": None,
        "tx_power": None,
        "security": None,
        "mode": None,
        "driver": None,
        "nearby": [],
        "source": None,
        "available_interfaces": [],
    }

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

    if wifi_ifaces:
        wifi_data["has_hardware"] = True
        wifi_data["available_interfaces"] = wifi_ifaces
        wifi_data["interface"] = wifi_ifaces[0]
    else:
        return {
            "has_hardware": False,
            "connected": False,
            "message": "No wireless network interfaces detected on this device.",
            "available_interfaces": [],
            "nearby": [],
        }

    primary_iface = wifi_data["interface"]

    # 1. Try nmcli
    if which("nmcli"):
        try:
            code, out, _ = run_command([
                "nmcli", "-t", "-f",
                "active,ssid,bssid,mode,chan,freq,rate,signal,security",
                "dev", "wifi", "list", "--rescan", "no"
            ], timeout=4)
            if code == 0 and out:
                nearby = []
                for line in out.splitlines():
                    parts = re.split(r"(?<!\\):", line)
                    if len(parts) >= 8:
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
                        net_item = {
                            "ssid": raw_ssid or "<Hidden SSID>",
                            "bssid": raw_bssid,
                            "mode": mode,
                            "channel": chan,
                            "frequency": freq,
                            "rate": rate,
                            "signal": sig_num,
                            "security": sec or "Open",
                            "is_current": is_active,
                        }
                        nearby.append(net_item)

                        if is_active:
                            wifi_data["connected"] = True
                            wifi_data["ssid"] = raw_ssid
                            wifi_data["bssid"] = raw_bssid
                            wifi_data["channel"] = chan
                            wifi_data["frequency"] = freq
                            wifi_data["bitrate"] = rate
                            wifi_data["signal_percent"] = sig_num
                            wifi_data["security"] = sec or "Open"
                            wifi_data["mode"] = mode
                            wifi_data["source"] = "nmcli"
                wifi_data["nearby"] = nearby[:20]
        except Exception:
            pass

    # 2. Try iwconfig
    if which("iwconfig"):
        try:
            code, out, _ = run_command(["iwconfig", primary_iface], timeout=3)
            if code == 0 and out:
                essid_m = re.search(r'ESSID:"([^"]+)"', out)
                if essid_m:
                    wifi_data["ssid"] = essid_m.group(1)
                    wifi_data["connected"] = True

                ap_m = re.search(r"Access Point:\s*([0-9A-Fa-f:]{17})", out)
                if ap_m:
                    wifi_data["bssid"] = ap_m.group(1)
                    wifi_data["connected"] = True

                rate_m = re.search(r"Bit Rate[=:]([\d.]+ \S+)", out)
                if rate_m:
                    wifi_data["bitrate"] = rate_m.group(1)

                freq_m = re.search(r"Frequency[=:]([\d.]+ \S+)", out)
                if freq_m:
                    wifi_data["frequency"] = freq_m.group(1)

                tx_m = re.search(r"Tx-Power[=:]([\d.]+ \S+)", out)
                if tx_m:
                    wifi_data["tx_power"] = tx_m.group(1)

                qual_m = re.search(r"Link Quality=([0-9/]+)", out)
                if qual_m:
                    wifi_data["quality"] = qual_m.group(1)
                    try:
                        q_parts = qual_m.group(1).split("/")
                        if len(q_parts) == 2 and float(q_parts[1]) > 0:
                            q_percent = int((float(q_parts[0]) / float(q_parts[1])) * 100)
                            if wifi_data["signal_percent"] is None:
                                wifi_data["signal_percent"] = min(100, max(0, q_percent))
                    except Exception:
                        pass

                sig_m = re.search(r"Signal level[=:](-?[\d.]+ \S+)", out)
                if sig_m:
                    wifi_data["signal_dbm"] = sig_m.group(1)

                mode_m = re.search(r"Mode:(\S+)", out)
                if mode_m and not wifi_data.get("mode"):
                    wifi_data["mode"] = mode_m.group(1)

                if not wifi_data.get("source"):
                    wifi_data["source"] = "iwconfig"
        except Exception:
            pass

    # 3. Try iw
    if which("iw") and (not wifi_data["connected"] or not wifi_data["signal_percent"]):
        try:
            code, out, _ = run_command(["iw", "dev", primary_iface, "link"], timeout=3)
            if code == 0 and "Connected to" in out:
                wifi_data["connected"] = True
                bssid_m = re.search(r"Connected to ([0-9a-f:]{17})", out, re.IGNORECASE)
                if bssid_m and not wifi_data.get("bssid"):
                    wifi_data["bssid"] = bssid_m.group(1).upper()
                ssid_m = re.search(r"SSID:\s*(.+)", out)
                if ssid_m and not wifi_data.get("ssid"):
                    wifi_data["ssid"] = ssid_m.group(1).strip()
                freq_m = re.search(r"freq:\s*(\d+)", out)
                if freq_m and not wifi_data.get("frequency"):
                    freq_val = int(freq_m.group(1))
                    wifi_data["frequency"] = f"{freq_val / 1000.0:.3f} GHz"
                sig_m = re.search(r"signal:\s*(-?[\d.]+)\s*dBm", out)
                if sig_m and not wifi_data.get("signal_dbm"):
                    dbm_val = float(sig_m.group(1))
                    wifi_data["signal_dbm"] = f"{dbm_val} dBm"
                    if wifi_data["signal_percent"] is None:
                        pct = int(max(0, min(100, 2 * (dbm_val + 100))))
                        wifi_data["signal_percent"] = pct
                bit_m = re.search(r"tx bitrate:\s*([^\n]+)", out)
                if bit_m and not wifi_data.get("bitrate"):
                    wifi_data["bitrate"] = bit_m.group(1).strip()
                if not wifi_data.get("source"):
                    wifi_data["source"] = "iw"
        except Exception:
            pass

    # 4. Try /proc/net/wireless
    if os.path.exists("/proc/net/wireless"):
        try:
            with open("/proc/net/wireless") as f:
                for line in f:
                    if primary_iface in line:
                        p = line.split()
                        if len(p) >= 4:
                            qual = p[2].rstrip(".")
                            level = p[3].rstrip(".")
                            if not wifi_data.get("quality") and qual:
                                wifi_data["quality"] = qual
                            if not wifi_data.get("signal_dbm") and level:
                                wifi_data["signal_dbm"] = f"{level} dBm"
                                if wifi_data["signal_percent"] is None:
                                    try:
                                        dbm = float(level)
                                        pct = int(max(0, min(100, 2 * (dbm + 100))))
                                        wifi_data["signal_percent"] = pct
                                    except Exception:
                                        pass
                            wifi_data["connected"] = True
        except Exception:
            pass

    # 5. Check rfkill
    rfkill_blocked = False
    if which("rfkill"):
        try:
            code, out, _ = run_command(["rfkill", "list", "wifi"], timeout=2)
            if code == 0 and "Soft blocked: yes" in out:
                rfkill_blocked = True
        except Exception:
            pass
    wifi_data["rfkill_blocked"] = rfkill_blocked

    return wifi_data


def scan_wifi_networks() -> list[dict]:
    """Trigger an active scan for nearby WiFi networks."""
    if which("nmcli"):
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
                    parts = re.split(r"(?<!\\):", line)
                    if len(parts) >= 8:
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
                        results.append({
                            "ssid": raw_ssid or "<Hidden SSID>",
                            "bssid": raw_bssid,
                            "mode": mode,
                            "channel": chan,
                            "frequency": freq,
                            "rate": rate,
                            "signal": sig_num,
                            "security": sec or "Open",
                            "is_current": is_active,
                        })
                return results[:25]
        except Exception:
            pass
    return []


def get_dns_info() -> dict:
    """
    Get DNS server configuration, discovering upstream servers across
    systemd-resolved, nmcli, resolv.conf, and fallback files.
    """
    raw_servers = []
    search_domains = []
    has_local_stub = False

    # 1. Try resolvectl or systemd-resolve
    for cmd in [["resolvectl", "status"], ["systemd-resolve", "--status"]]:
        try:
            p_code, p_out, _ = run_command(cmd, timeout=3)
            if p_code == 0 and p_out:
                curr_matches = re.findall(r"Current DNS Server:\s*(\S+)", p_out)
                srv_matches = re.findall(r"DNS Servers:\s*([^\n]+)", p_out)
                dom_matches = re.findall(r"DNS Domain:\s*([^\n]+)", p_out)

                for s_line in srv_matches:
                    for s in s_line.split():
                        if s not in raw_servers:
                            raw_servers.append(s)
                for c in curr_matches:
                    if c in raw_servers:
                        raw_servers.remove(c)
                    raw_servers.insert(0, c)
                for d_line in dom_matches:
                    for d in d_line.split():
                        if d not in search_domains and d != ".":
                            search_domains.append(d)
                if raw_servers:
                    break
        except Exception:
            pass

    # 2. Try /run/systemd/resolve/resolv.conf
    if os.path.exists("/run/systemd/resolve/resolv.conf"):
        try:
            with open("/run/systemd/resolve/resolv.conf") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("nameserver"):
                        p = line.split()
                        if len(p) > 1 and p[1] not in raw_servers:
                            raw_servers.append(p[1])
                    elif line.startswith("search"):
                        p = line.split()
                        for d in p[1:]:
                            if d not in search_domains and d != ".":
                                search_domains.append(d)
        except Exception:
            pass

    # 3. Try nmcli dev show
    if not raw_servers and which("nmcli"):
        try:
            code, out, _ = run_command(["nmcli", "dev", "show"], timeout=3)
            if code == 0 and out:
                for line in out.splitlines():
                    if "IP4.DNS" in line or "IP6.DNS" in line:
                        parts = line.split(":", 1)
                        if len(parts) > 1:
                            val = parts[1].strip()
                            if val and val not in raw_servers:
                                raw_servers.append(val)
        except Exception:
            pass

    # 4. Fallback to /etc/resolv.conf
    if os.path.exists("/etc/resolv.conf"):
        try:
            with open("/etc/resolv.conf") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("nameserver"):
                        parts = line.split()
                        if len(parts) > 1:
                            srv = parts[1]
                            if srv.startswith("127."):
                                has_local_stub = True
                            elif srv not in raw_servers:
                                raw_servers.append(srv)
                    elif line.startswith("search"):
                        parts = line.split()
                        for d in parts[1:]:
                            if d not in search_domains and d != ".":
                                search_domains.append(d)
        except Exception:
            pass

    if any(s.startswith("127.") for s in raw_servers):
        has_local_stub = True
        raw_servers = [s for s in raw_servers if not s.startswith("127.")]

    if not raw_servers and has_local_stub:
        raw_servers = ["127.0.0.53"]

    servers_list = []
    for idx, s in enumerate(raw_servers):
        is_stub = s.startswith("127.")
        provider = get_known_dns_provider(s)
        servers_list.append({
            "ip": s,
            "provider": provider,
            "is_primary": (idx == 0),
            "is_stub": is_stub,
        })

    return {
        "servers": servers_list,
        "upstream_ips": raw_servers,
        "has_local_stub": has_local_stub,
        "stub_ip": "127.0.0.53" if has_local_stub else None,
        "search_domains": search_domains,
        "resolver_type": "systemd-resolved" if has_local_stub else "direct",
    }


def get_dns_servers() -> list[str]:
    """Backward-compatible DNS list function."""
    dns_info = get_dns_info()
    return dns_info.get("upstream_ips", [])


def dns_lookup(domain: str = "google.com") -> dict:
    """
    Perform a live DNS lookup diagnostic for a given domain and record latency.
    """
    domain = domain.strip().lower()
    if not domain:
        return {"domain": domain, "success": False, "error": "Empty domain name"}

    if not re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", domain):
        return {"domain": domain, "success": False, "error": "Invalid domain format"}

    start_time = time.perf_counter()
    try:
        addr_info = socket.getaddrinfo(domain, None)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        ipv4_records = []
        ipv6_records = []
        for item in addr_info:
            ip_str = item[4][0]
            if item[0] == socket.AF_INET and ip_str not in ipv4_records:
                ipv4_records.append(ip_str)
            elif item[0] == socket.AF_INET6 and ip_str not in ipv6_records:
                ipv6_records.append(ip_str)

        return {
            "domain": domain,
            "success": True,
            "time_ms": round(elapsed_ms, 1),
            "ipv4": ipv4_records,
            "ipv6": ipv6_records,
            "count": len(ipv4_records) + len(ipv6_records),
        }
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return {
            "domain": domain,
            "success": False,
            "time_ms": round(elapsed_ms, 1),
            "error": str(e),
            "ipv4": [],
            "ipv6": [],
            "count": 0,
        }


def ping_test(target: str = "8.8.8.8", count: int = 3) -> dict:
    """
    Run ping test supporting both standard iputils and busybox formats.
    Returns structured stats: transmitted, received, packet loss, and latencies.
    """
    target = target.strip()
    if not target:
        target = "8.8.8.8"

    if not re.match(r"^[a-zA-Z0-9.:_-]+$", target):
        return {
            "target": target,
            "success": False,
            "error": "Invalid ping target characters",
            "output": "",
            "avg_latency": None,
        }

    count = max(1, min(count, 10))
    code, out, err = run_command(["ping", "-c", str(count), "-W", "2", target], timeout=12 + count * 2)

    result = {
        "target": target,
        "success": False,
        "output": out,
        "error": err,
        "transmitted": count,
        "received": 0,
        "packet_loss_percent": 100.0,
        "min_latency": None,
        "avg_latency": None,
        "max_latency": None,
        "mdev_latency": None,
    }

    stat_m = re.search(r"(\d+)\s+packets transmitted,\s+(\d+)\s+(?:packets\s+)?received.*?([\d.]+)%\s+packet loss", out, re.IGNORECASE)
    if stat_m:
        tx = int(stat_m.group(1))
        rx = int(stat_m.group(2))
        loss = float(stat_m.group(3))
        result["transmitted"] = tx
        result["received"] = rx
        result["packet_loss_percent"] = loss
        if rx > 0:
            result["success"] = True
    elif "64 bytes from" in out or "bytes from" in out:
        result["received"] = len(re.findall(r"bytes from", out))
        result["success"] = True
        result["packet_loss_percent"] = max(0.0, ((count - result["received"]) / count) * 100.0)

    rtt_m = re.search(r"rtt\s+min/avg/max/mdev\s*=\s*([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)", out)
    if rtt_m:
        result["min_latency"] = float(rtt_m.group(1))
        result["avg_latency"] = float(rtt_m.group(2))
        result["max_latency"] = float(rtt_m.group(3))
        result["mdev_latency"] = float(rtt_m.group(4))
    else:
        bb_m = re.search(r"(?:round-trip|rtt)\s+min/avg/max\s*=\s*([\d.]+)/([\d.]+)/([\d.]+)", out)
        if bb_m:
            result["min_latency"] = float(bb_m.group(1))
            result["avg_latency"] = float(bb_m.group(2))
            result["max_latency"] = float(bb_m.group(3))

    return result


def get_network_summary() -> dict:
    """
    Produce a top-level summary of active network state:
    Primary IP, default gateway, active DNS, total traffic, and online status.
    """
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

    return {
        "is_online": is_online,
        "primary_interface": default_dev,
        "primary_type": primary_type,
        "primary_ip": primary_ip,
        "primary_mac": primary_mac,
        "default_gateway": default_gw,
        "primary_dns": primary_dns,
        "primary_dns_provider": primary_dns_provider,
        "total_rx_fmt": format_bytes(total_rx),
        "total_tx_fmt": format_bytes(total_tx),
        "wifi_connected": wifi.get("connected", False),
        "wifi_ssid": wifi.get("ssid"),
        "wifi_signal": wifi.get("signal_percent"),
    }
