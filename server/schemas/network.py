from typing import Any

from pydantic import BaseModel


class PingResponse(BaseModel):
    target: str
    transmitted: int
    received: int
    packet_loss: float
    avg_latency_ms: float | None = None
    output: str | None = None
    success: bool


class DnsQueryResponse(BaseModel):
    domain: str
    resolved_ip: str | None = None
    latency_ms: float | None = None
    success: bool
    error: str | None = None


class WifiNetworkItem(BaseModel):
    ssid: str
    bssid: str | None = None
    signal: int | None = None
    frequency: str | None = None
    security: str | None = None


class NetworkSummaryResponse(BaseModel):
    summary: dict[str, Any]
    interfaces: list[dict[str, Any]]
    wifi: dict[str, Any]
    dns: list[str]
    dns_details: dict[str, Any]
    gateways: list[dict[str, Any]]
