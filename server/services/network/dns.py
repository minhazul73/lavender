"""
DNS configuration and lookup diagnostics.
"""
import os
import re
import socket
import time

from server.services.network.models import DNSInfo, DNSLookupResult, DNSServer
from server.services.network.utils import get_known_dns_provider, run_command
from server.utils.cmd import which


def get_dns_info() -> dict:
    """
    Get DNS server configuration, discovering upstream servers across
    systemd-resolved, nmcli, resolv.conf, and fallback files.

    Returns:
        Dictionary with DNS server details, upstream IPs, and resolver type
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
        servers_list.append(DNSServer(
            ip=s,
            provider=provider,
            is_primary=(idx == 0),
            is_stub=is_stub,
        ))

    dns_info = DNSInfo(
        servers=servers_list,
        upstream_ips=raw_servers,
        has_local_stub=has_local_stub,
        stub_ip="127.0.0.53" if has_local_stub else None,
        search_domains=search_domains,
        resolver_type="systemd-resolved" if has_local_stub else "direct",
    )

    return dns_info.to_dict()


def get_dns_servers() -> list[str]:
    """
    Backward-compatible DNS list function.

    Returns:
        List of upstream DNS server IP strings
    """
    dns_info = get_dns_info()
    return dns_info.get("upstream_ips", [])


def dns_lookup(domain: str = "google.com") -> dict:
    """
    Perform a live DNS lookup diagnostic for a given domain and record latency.

    Args:
        domain: Domain name to resolve

    Returns:
        Dictionary with lookup results including resolved IPs and timing
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

        result = DNSLookupResult(
            domain=domain,
            success=True,
            time_ms=round(elapsed_ms, 1),
            ipv4=ipv4_records,
            ipv6=ipv6_records,
            count=len(ipv4_records) + len(ipv6_records),
        )
        return result.to_dict()
    except socket.gaierror:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        result = DNSLookupResult(
            domain=domain,
            success=False,
            time_ms=round(elapsed_ms, 1),
            error="Domain resolution failed",
            ipv4=[],
            ipv6=[],
            count=0,
        )
        return result.to_dict()
    except Exception:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        result = DNSLookupResult(
            domain=domain,
            success=False,
            time_ms=round(elapsed_ms, 1),
            error="DNS lookup failed",
            ipv4=[],
            ipv6=[],
            count=0,
        )
        return result.to_dict()
