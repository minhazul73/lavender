from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class PingResponse(BaseModel):
    target: str
    transmitted: int
    received: int
    packet_loss: float
    avg_latency_ms: Optional[float] = None
    output: Optional[str] = None
    success: bool


class DnsQueryResponse(BaseModel):
    domain: str
    resolved_ip: Optional[str] = None
    latency_ms: Optional[float] = None
    success: bool
    error: Optional[str] = None


class WifiNetworkItem(BaseModel):
    ssid: str
    bssid: Optional[str] = None
    signal: Optional[int] = None
    frequency: Optional[str] = None
    security: Optional[str] = None


class NetworkSummaryResponse(BaseModel):
    summary: Dict[str, Any]
    interfaces: List[Dict[str, Any]]
    wifi: Dict[str, Any]
    dns: List[str]
    dns_details: Dict[str, Any]
    gateways: List[Dict[str, Any]]
