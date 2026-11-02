"""
Network API routes for Lavender.
Provides network overview, interface inspection, WiFi scanning, ping, and DNS resolution.
"""
import re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from server.auth.deps import require_session
from server.auth.session import UserSession
from server.services.network import (
    dns_lookup,
    get_dns_info,
    get_gateways,
    get_ip_addresses,
    get_network_summary,
    get_wifi_info,
    ping_test,
    scan_wifi_networks,
)

router = APIRouter()


@router.get("", summary="Get complete network information")
@router.get("/", include_in_schema=False)
@router.get("/network", include_in_schema=False)
async def api_network(session: UserSession = Depends(require_session)):
    """Get complete network summary, interface IPs, WiFi link details, and routes."""
    dns_info = get_dns_info()
    return {
        "summary": get_network_summary(),
        "interfaces": get_ip_addresses(),
        "wifi": get_wifi_info(),
        "dns": dns_info.get("upstream_ips", []),
        "dns_details": dns_info,
        "gateways": get_gateways(),
    }


@router.get("/ping", summary="Ping a target IP or host")
@router.get("/network/ping", include_in_schema=False)
async def api_ping(
    target: str = Query("8.8.8.8", description="Target IP or hostname to ping"),
    count: int = Query(3, ge=1, le=10, description="Ping packet count"),
    session: UserSession = Depends(require_session),
):
    """Ping a remote address and return round-trip latency and loss statistics."""
    target_clean = target.strip()
    if not re.match(r"^[a-zA-Z0-9.:_-]+$", target_clean) or target_clean.startswith("-"):
        raise HTTPException(status_code=400, detail="Invalid target format")
    return ping_test(target_clean, count=count)


@router.get("/dns-query", summary="DNS resolution test")
@router.get("/network/dns-query", include_in_schema=False)
async def api_dns_query(
    domain: str = Query("google.com", description="Domain to resolve"),
    session: UserSession = Depends(require_session),
):
    """Test resolving a domain and measure lookup latency."""
    domain_clean = domain.strip().lower()
    if not re.match(r"^[a-zA-Z0-9.:_-]+$", domain_clean) or domain_clean.startswith("-"):
        raise HTTPException(status_code=400, detail="Invalid domain format")
    return dns_lookup(domain_clean)


@router.post("/wifi-scan", summary="Scan nearby WiFi SSIDs")
@router.post("/network/wifi-scan", include_in_schema=False)
async def api_wifi_scan(
    session: UserSession = Depends(require_session),
):
    """Trigger WiFi scan for nearby broadcast networks."""
    return {"networks": scan_wifi_networks()}
