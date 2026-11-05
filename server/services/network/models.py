"""
Data models for network service.
Replaces raw dict structures with typed dataclasses.
"""
from dataclasses import dataclass, field


@dataclass
class GatewayInfo:
    """Network default gateway information."""
    gateway: str
    interface: str
    protocol: str = "static"
    metric: int = 0
    prefsrc: str = ""


@dataclass
class IPAddressInfo:
    """Single IP address assignment."""
    address: str
    cidr: str
    broadcast: str | None = None
    scope: str = "global"


@dataclass
class InterfaceStats:
    """Network interface statistics."""
    rx_bytes: int = 0
    tx_bytes: int = 0
    rx_packets: int = 0
    tx_packets: int = 0
    rx_errors: int = 0
    tx_errors: int = 0


@dataclass
class NetworkInterface:
    """Network interface information."""
    name: str
    type: str
    category: str
    state: str
    is_up: bool
    is_default: bool
    mac: str | None = None
    mtu: int = 0
    speed: str | None = None
    flags: list = field(default_factory=list)
    addresses: list = field(default_factory=list)
    ipv4: list = field(default_factory=list)
    ipv6: list = field(default_factory=list)
    rx_bytes_fmt: str = "0 B"
    tx_bytes_fmt: str = "0 B"
    stats: InterfaceStats = field(default_factory=InterfaceStats)

    def to_dict(self) -> dict:
        """Convert to dictionary for backward compatibility."""
        return {
            "name": self.name,
            "type": self.type,
            "category": self.category,
            "state": self.state,
            "is_up": self.is_up,
            "is_default": self.is_default,
            "mac": self.mac,
            "mtu": self.mtu,
            "speed": self.speed,
            "flags": self.flags,
            "addresses": self.addresses,
            "ipv4": self.ipv4,
            "ipv6": self.ipv6,
            "rx_bytes_fmt": self.rx_bytes_fmt,
            "tx_bytes_fmt": self.tx_bytes_fmt,
            "stats": {
                "rx_bytes": self.stats.rx_bytes,
                "tx_bytes": self.stats.tx_bytes,
                "rx_packets": self.stats.rx_packets,
                "tx_packets": self.stats.tx_packets,
                "rx_errors": self.stats.rx_errors,
                "tx_errors": self.stats.tx_errors,
            },
        }


@dataclass
class WiFiNetwork:
    """Nearby WiFi network information."""
    ssid: str
    bssid: str
    mode: str
    channel: str
    frequency: str
    rate: str
    signal: int
    security: str = "Open"
    is_current: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for backward compatibility."""
        return {
            "ssid": self.ssid,
            "bssid": self.bssid,
            "mode": self.mode,
            "channel": self.channel,
            "frequency": self.frequency,
            "rate": self.rate,
            "signal": self.signal,
            "security": self.security,
            "is_current": self.is_current,
        }


@dataclass
class WiFiInfo:
    """WiFi adapter and connection information."""
    has_hardware: bool = False
    connected: bool = False
    interface: str | None = None
    ssid: str | None = None
    bssid: str | None = None
    signal_percent: int | None = None
    signal_dbm: str | None = None
    quality: str | None = None
    frequency: str | None = None
    channel: str | None = None
    bitrate: str | None = None
    tx_power: str | None = None
    security: str | None = None
    mode: str | None = None
    driver: str | None = None
    nearby: list = field(default_factory=list)
    source: str | None = None
    available_interfaces: list = field(default_factory=list)
    rfkill_blocked: bool = False
    message: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for backward compatibility."""
        return {
            "has_hardware": self.has_hardware,
            "connected": self.connected,
            "interface": self.interface,
            "ssid": self.ssid,
            "bssid": self.bssid,
            "signal_percent": self.signal_percent,
            "signal_dbm": self.signal_dbm,
            "quality": self.quality,
            "frequency": self.frequency,
            "channel": self.channel,
            "bitrate": self.bitrate,
            "tx_power": self.tx_power,
            "security": self.security,
            "mode": self.mode,
            "driver": self.driver,
            "nearby": [n.to_dict() if isinstance(n, WiFiNetwork) else n for n in self.nearby],
            "source": self.source,
            "available_interfaces": self.available_interfaces,
            "rfkill_blocked": self.rfkill_blocked,
            "message": self.message,
        }


@dataclass
class DNSServer:
    """DNS server information."""
    ip: str
    provider: str
    is_primary: bool = False
    is_stub: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for backward compatibility."""
        return {
            "ip": self.ip,
            "provider": self.provider,
            "is_primary": self.is_primary,
            "is_stub": self.is_stub,
        }


@dataclass
class DNSInfo:
    """DNS configuration information."""
    servers: list = field(default_factory=list)
    upstream_ips: list = field(default_factory=list)
    has_local_stub: bool = False
    stub_ip: str | None = None
    search_domains: list = field(default_factory=list)
    resolver_type: str = "direct"

    def to_dict(self) -> dict:
        """Convert to dictionary for backward compatibility."""
        return {
            "servers": [s.to_dict() if isinstance(s, DNSServer) else s for s in self.servers],
            "upstream_ips": self.upstream_ips,
            "has_local_stub": self.has_local_stub,
            "stub_ip": self.stub_ip,
            "search_domains": self.search_domains,
            "resolver_type": self.resolver_type,
        }


@dataclass
class DNSLookupResult:
    """DNS lookup result for a domain."""
    domain: str
    success: bool
    time_ms: float
    ipv4: list = field(default_factory=list)
    ipv6: list = field(default_factory=list)
    count: int = 0
    error: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for backward compatibility."""
        return {
            "domain": self.domain,
            "success": self.success,
            "time_ms": self.time_ms,
            "ipv4": self.ipv4,
            "ipv6": self.ipv6,
            "count": self.count,
            "error": self.error,
        }


@dataclass
class PingResult:
    """Ping test result."""
    target: str
    success: bool
    output: str
    error: str = ""
    transmitted: int = 0
    received: int = 0
    packet_loss_percent: float = 100.0
    min_latency: float | None = None
    avg_latency: float | None = None
    max_latency: float | None = None
    mdev_latency: float | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for backward compatibility."""
        return {
            "target": self.target,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "transmitted": self.transmitted,
            "received": self.received,
            "packet_loss_percent": self.packet_loss_percent,
            "min_latency": self.min_latency,
            "avg_latency": self.avg_latency,
            "max_latency": self.max_latency,
            "mdev_latency": self.mdev_latency,
        }


@dataclass
class NetworkSummary:
    """High-level network state summary."""
    is_online: bool
    primary_interface: str | None
    primary_type: str
    primary_ip: str | None
    primary_mac: str | None
    default_gateway: str | None
    primary_dns: str | None
    primary_dns_provider: str | None
    total_rx_fmt: str = "0 B"
    total_tx_fmt: str = "0 B"
    wifi_connected: bool = False
    wifi_ssid: str | None = None
    wifi_signal: int | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for backward compatibility."""
        return {
            "is_online": self.is_online,
            "primary_interface": self.primary_interface,
            "primary_type": self.primary_type,
            "primary_ip": self.primary_ip,
            "primary_mac": self.primary_mac,
            "default_gateway": self.default_gateway,
            "primary_dns": self.primary_dns,
            "primary_dns_provider": self.primary_dns_provider,
            "total_rx_fmt": self.total_rx_fmt,
            "total_tx_fmt": self.total_tx_fmt,
            "wifi_connected": self.wifi_connected,
            "wifi_ssid": self.wifi_ssid,
            "wifi_signal": self.wifi_signal,
        }
