# Network Module Analysis & Decomposition Plan

## Current Architecture Analysis

### Overview
The `server/services/network.py` module (930 lines) provides comprehensive network functionality for the Lavender dashboard, covering WiFi management, interface enumeration, DNS resolution, ping testing, and network summary generation.

### Key Components Identified

#### 1. Core Functions (9 total)
- `run_command()` - Command execution wrapper
- `format_bytes()` - Human-readable byte formatting
- `get_known_dns_provider()` - DNS provider identification
- `get_gateways()` - Network gateway discovery
- `get_ip_addresses()` - Interface enumeration with detailed metadata
- `get_wifi_info()` - WiFi connection scanning and status
- `scan_wifi_networks()` - Active WiFi network scanning
- `get_dns_info()` - DNS server configuration discovery
- `get_network_summary()` - High-level network status summary

#### 2. Data Structures (Dictionary-based)
All functions currently return raw dictionaries with inconsistent structures:
- Network interfaces: `dict` with keys like `name`, `type`, `state`, `mac`, `mtu`, `ipv4`, `ipv6`, `stats`
- WiFi data: `dict` with keys like `has_hardware`, `connected`, `ssid`, `bssid`, `signal_percent`
- DNS info: `dict` with keys like `servers`, `upstream_ips`, `has_local_stub`
- Ping results: `dict` with keys like `target`, `transmitted`, `received`, `packet_loss`

#### 3. Dependencies
- **External Commands**: `ip`, `iwconfig`, `iw`, `nmcli`, `wpa_cli`, `rfkill`, `ping`, `resolvectl`, `systemd-resolve`
- **System Files**: `/proc/net/dev`, `/proc/net/route`, `/proc/net/wireless`, `/sys/class/net/*`, `/etc/resolv.conf`
- **Internal Dependencies**: 
  - `server.core.executor.get_executor()` for command execution
  - `server.utils.cmd.which()` for command detection
  - `server.utils.network` for validation utilities

#### 4. External Interfaces
- **API Layer**: `server.api.network` - HTTP endpoints for network data
- **SSE Collector**: `server.services.collectors.network.NetworkCollector` - Real-time network rate monitoring
- **Test Suite**: `tests/unit/test_network_services.py` - Unit tests for service functions

## Proposed Decomposition Strategy

### Target Submodule Structure

```
server/services/network/
├── __init__.py              # Public API exports
├── models.py                # Dataclass definitions
├── interfaces.py           # Network interface management
├── wifi.py                  # WiFi-specific functionality
├── dns.py                   # DNS resolution and configuration
├── commands.py              # Command execution utilities
├── formatters.py            # Data formatting helpers
└── collectors.py           # Real-time metric collection
```

### Dataclass Design

#### 1. Network Interface Models (`models.py`)
```python
@dataclass(frozen=True)
class NetworkInterface:
    name: str
    type: str  # "ethernet", "wireless", "loopback", "bridge", "virtual", "cellular"
    category: str  # Same as type for now
    state: str  # "UP", "DOWN", "UNKNOWN"
    is_up: bool
    is_default: bool
    mac: Optional[str]
    mtu: int
    speed: Optional[str]
    flags: List[str]
    addresses: List[str]
    ipv4: List[IPv4Address]
    ipv6: List[IPv6Address]
    stats: InterfaceStatistics
    rx_bytes_fmt: str
    tx_bytes_fmt: str

@dataclass(frozen=True)
class InterfaceStatistics:
    rx_bytes: int
    tx_bytes: int
    rx_packets: int
    tx_packets: int
    rx_errors: int
    tx_errors: int

@dataclass(frozen=True)
class IPv4Address:
    address: str
    cidr: str
    broadcast: Optional[str]
    scope: str

@dataclass(frozen=True)
class IPv6Address:
    address: str
    cidr: str
    scope: str
```

#### 2. WiFi Models (`models.py`)
```python
@dataclass(frozen=True)
class WiFiNetwork:
    ssid: str
    bssid: Optional[str]
    signal: Optional[int]
    frequency: Optional[str]
    channel: Optional[str]
    security: Optional[str]
    mode: Optional[str]
    bitrate: Optional[str]
    is_current: bool = False

@dataclass(frozen=True)
class WiFiConnection:
    has_hardware: bool
    connected: bool
    interface: Optional[str]
    ssid: Optional[str]
    bssid: Optional[str]
    signal_percent: Optional[int]
    signal_dbm: Optional[str]
    quality: Optional[str]
    frequency: Optional[str]
    channel: Optional[str]
    bitrate: Optional[str]
    tx_power: Optional[str]
    security: Optional[str]
    mode: Optional[str]
    driver: Optional[str]
    rfkill_blocked: bool
    source: Optional[str]
    available_interfaces: List[str]
    nearby: List[WiFiNetwork]
```

#### 3. DNS Models (`models.py`)
```python
@dataclass(frozen=True)
class DNSServer:
    ip: str
    provider: str
    is_primary: bool
    is_stub: bool

@dataclass(frozen=True)
class DNSInfo:
    servers: List[DNSServer]
    upstream_ips: List[str]
    has_local_stub: bool
    stub_ip: Optional[str]
    search_domains: List[str]
    resolver_type: str

@dataclass(frozen=True)
class DNSLookupResult:
    domain: str
    success: bool
    time_ms: Optional[float]
    ipv4: List[str]
    ipv6: List[str]
    count: int
    error: Optional[str]
```

#### 4. Network Models (`models.py`)
```python
@dataclass(frozen=True)
class NetworkGateway:
    gateway: str
    interface: str
    protocol: str
    metric: int
    prefsrc: Optional[str]

@dataclass(frozen=True)
class NetworkSummary:
    is_online: bool
    primary_interface: Optional[str]
    primary_type: str
    primary_ip: Optional[str]
    primary_mac: Optional[str]
    default_gateway: Optional[str]
    primary_dns: Optional[str]
    primary_dns_provider: Optional[str]
    total_rx_fmt: str
    total_tx_fmt: str
    wifi_connected: bool
    wifi_ssid: Optional[str]
    wifi_signal: Optional[int]
```

#### 5. Testing Models (`models.py`)
```python
@dataclass(frozen=True)
class PingResult:
    target: str
    transmitted: int
    received: int
    packet_loss_percent: float
    min_latency: Optional[float]
    avg_latency: Optional[float]
    max_latency: Optional[float]
    mdev_latency: Optional[float]
    success: bool
    output: Optional[str]
    error: Optional[str]
```

### Submodule Responsibilities

#### 1. `interfaces.py` - Network Interface Management
- Functions: `get_ip_addresses()`, `get_gateways()`, `detect_wifi_interface()`
- Returns: `List[NetworkInterface]`, `List[NetworkGateway]`
- Dependencies: `commands.py`, `formatters.py`

#### 2. `wifi.py` - WiFi Functionality
- Functions: `get_wifi_info()`, `scan_wifi_networks()`, `parse_signal_strength()`
- Returns: `WiFiConnection`, `List[WiFiNetwork]`
- Dependencies: `interfaces.py`, `commands.py`

#### 3. `dns.py` - DNS Management
- Functions: `get_dns_info()`, `dns_lookup()`, `get_known_dns_provider()`
- Returns: `DNSInfo`, `DNSLookupResult`
- Dependencies: `commands.py`, `formatters.py`

#### 4. `commands.py` - Command Execution
- Functions: `run_command()`, `execute_wifi_scan()`, `execute_dns_query()`
- Returns: Command results, structured data
- Dependencies: `server.core.executor`

#### 5. `formatters.py` - Data Formatting
- Functions: `format_bytes()`, `format_signal_strength()`, `format_network_stats()`
- Returns: Formatted strings, computed values
- Dependencies: None

#### 6. `collectors.py` - Real-time Metrics
- Functions: `NetworkRateCollector` (existing), new collectors for WiFi/DNS
- Returns: Real-time metric streams
- Dependencies: `models.py`, `commands.py`

#### 7. `__init__.py` - Public API
- Exports: All public functions and dataclasses
- Maintains backward compatibility with existing API

### Migration Benefits

1. **Type Safety**: Dataclasses provide compile-time type checking
2. **Immutability**: Frozen dataclasses prevent accidental modification
3. **Consistency**: Standardized data structures across all functions
4. **Testability**: Easier to create test fixtures and mock objects
5. **Maintainability**: Smaller, focused modules are easier to understand and modify
6. **Documentation**: Self-documenting dataclasses with clear field purposes
7. **Performance**: Reduced dictionary manipulation overhead

### Backward Compatibility Strategy

1. **Public API Preservation**: All existing function signatures remain unchanged
2. **Internal Migration**: Replace dictionary returns with dataclasses internally
3. **Schema Updates**: Update `server/schemas/network.py` to use new dataclasses
4. **Gradual Migration**: Phase in dataclasses while maintaining legacy dict support

### Testing Considerations

1. **Unit Tests**: Update existing tests to work with dataclasses
2. **Integration Tests**: Ensure API responses remain compatible
3. **Performance Tests**: Verify no performance regression from dataclass overhead
4. **Edge Cases**: Test dataclass serialization/deserialization for API responses

## Implementation Priority

1. **Phase 1**: Dataclass definitions and models
2. **Phase 2**: Submodule creation with function migration
3. **Phase 3**: Schema updates and API compatibility
4. **Phase 4**: Testing and validation
5. **Phase 5**: Performance optimization and cleanup

This decomposition maintains all existing functionality while providing a more maintainable, type-safe, and well-structured codebase.