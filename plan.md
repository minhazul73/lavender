# Optimization Plan for Top Lavender Dashboard Modules

**Generated**: 2026-10-29
**Based on**: `top_modules.json` from Task t_7276d027
**Workspace**: `/home/rahat/.hermes/kanban/workspaces/t_d4383d6f`

---

## Module 1: `dashboard/services/live.py`

### Current State Summary

- **Lines of Code**: 1,430
- **Cyclomatic Complexity**: 317
- **Weighted Score**: 453,310 (complexity × LOC)
- **Optimization Category**: **Decompose**

**Key Hotspots**:
1. Single file contains 5 collector classes (CPUFreqCollector, RAMCollector, ThermalCollector, BatteryCollector, NetworkCollector) plus LiveMonitor orchestration
2. Mixes three concerns: metric collection logic, sysfs parsing, and SSE stream coordination
3. `CPUFreqCollector.collect()` (lines 358–420): 63 lines with nested logic for frequency discovery, per-core usage calculation, and load average reads
4. `ThermalCollector.collect()` (lines 680–750 approx): similar pattern with thermal zone discovery and temp parsing
5. Repeated patterns: each collector implements its own `_discover_*()` method, sysfs reading, and error handling

**Structural Issues**:
- No physical separation between collector implementations (all in one file)
- `RingBuffer` class (lines 82–112) is defined in the same file as collectors
- Helper functions (`_read_file`, `_read_int`, `_read_float`, `_parse_proc_stat`, `_calc_cpu_usage`) are module-level but only used by specific collectors
- `LiveMonitor` class (not shown in excerpt) coordinates all collectors but lives in the same file

### Proposed Refactoring Steps

#### Step 1: Create Directory Structure
```
dashboard/services/
├── live.py                 # Keep only LiveMonitor + SSE generator
├── collectors/
│   ├── __init__.py
│   ├── base.py             # MetricCollector base class + RingBuffer + CollectorStats
│   ├── cpu.py              # CPUFreqCollector + CPUCoreInfo + _parse_proc_stat
│   ├── ram.py              # RAMCollector
│   ├── thermal.py          # ThermalCollector + ThermalZone
│   ├── battery.py          # BatteryCollector
│   └── network.py          # NetworkCollector (not to be confused with dashboard/services/network.py)
```

#### Step 2: Extract Base Class (`collectors/base.py`)
```python
"""Base collector protocol and shared utilities."""

from __future__ import annotations
import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Any, Optional, List

@dataclass
class CollectorStats:
    """Running stats for a single collector."""
    sample_count: int = 0
    last_error: Optional[str] = None
    errors_in_row: int = 0

class RingBuffer:
    """Fixed-size circular buffer for a single metric stream."""
    __slots__ = ("_buf", "_size")

    def __init__(self, size: int) -> None:
        self._buf: deque = deque(maxlen=size)
        self._size = size

    def append(self, value: float) -> None:
        self._buf.append(value)

    def values(self) -> List[float]:
        return list(self._buf)

    @property
    def is_empty(self) -> bool:
        return len(self._buf) == 0

class MetricCollector:
    """Base class for a single-metric SSE collector.

    Subclasses implement:
      - collect() -> dict   (the current metric sample)
      - get_buffer()        (RingBuffer for sparkline/history)
    """
    __slots__ = ("_interval_ms", "_buffer", "_stats", "_stop_event", "_task", "_buffer_key")

    def __init__(self, interval_ms: int, history_size: int, buffer_key: str) -> None:
        self._interval_ms = interval_ms
        self._buffer = RingBuffer(history_size)
        self._stats = CollectorStats()
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task[None]] = None
        self._buffer_key = buffer_key

    @property
    def buffer(self) -> RingBuffer:
        return self._buffer

    @property
    def stats(self) -> CollectorStats:
        return self._stats

    async def collect(self) -> dict:
        raise NotImplementedError

    async def _run_loop(self) -> None:
        """Main collection loop. Sleep-based, not fixed-schedule."""
        interval_s = self._interval_ms / 1000.0
        while not self._stop_event.is_set():
            try:
                sample = await self.collect()
                self._on_sample(sample)
                self._stats.errors_in_row = 0
                self._stats.last_error = None
            except Exception as exc:
                self._stats.errors_in_row += 1
                self._stats.last_error = str(exc)
                await asyncio.sleep(min(interval_s, 1.0))
            await asyncio.sleep(interval_s)

    def _on_sample(self, sample: dict) -> None:
        """Called for each successful sample. Subclasses may override."""
        pass

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop_event.clear()
        self._task = loop.create_task(self._run_loop(), name=f"collector-{self._buffer_key}")

    def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            try:
                self._task.cancel()
            except RuntimeError:
                pass
            self._task = None
```

#### Step 3: Extract CPU Collector (`collectors/cpu.py`)
**Key changes**:
- Move `_parse_proc_stat()`, `_calc_cpu_usage()`, `CPUCoreInfo`, and `CPUFreqCollector` here
- Import `MetricCollector`, `RingBuffer`, `CollectorStats` from `base`
- Keep sysfs paths as constants at module top

**Pseudocode**:
```python
from .base import MetricCollector, RingBuffer, CollectorStats

CPU_DIR = "/sys/devices/system/cpu"

class CPUFreqCollector(MetricCollector):
    def __init__(self, interval_ms=SSE_CPU_INTERVAL_MS, history_size=20):
        super().__init__(interval_ms, history_size, "cpu")
        self._cpus: List[CPUCoreInfo] = []
        self._has_cpufreq = False
        self._prev_stat: List[Optional[dict]] = []
        self._curr_stat: List[Optional[dict]] = []

    async def collect(self) -> dict:
        # 1. Discover CPUs every 5s
        # 2. Read per-core freq from sysfs
        # 3. Parse /proc/stat for usage deltas
        # 4. Return structured dict with cpufreq_available flag
        ...
```

#### Step 4: Extract Other Collectors
Repeat Step 3 pattern for:
- `collectors/ram.py`: `RAMCollector` + `_parse_meminfo()`
- `collectors/thermal.py`: `ThermalCollector` + `ThermalZone` + `THERMAL_NAME_MAP`
- `collectors/battery.py`: `BatteryCollector` + battery-specific helpers
- `collectors/network.py`: `NetworkCollector` (note: this is for SSE metric collection, NOT the same as `dashboard/services/network.py` which is for WiFi/network management)

#### Step 5: Refactor `live.py` to Orchestrate Only
**Keep in `live.py`**:
- `LiveMonitor` class (coordinates all collectors)
- SSE generator function (`sse_generator`)
- Router endpoint (`live_sse`)

**Remove from `live.py`**:
- All collector class definitions
- `RingBuffer`, `CollectorStats`, `MetricCollector`
- Helper functions specific to individual collectors

**New imports**:
```python
from dashboard.services.collectors.cpu import CPUFreqCollector
from dashboard.services.collectors.ram import RAMCollector
from dashboard.services.collectors.thermal import ThermalCollector
from dashboard.services.collectors.battery import BatteryCollector
from dashboard.services.collectors.network import NetworkCollector
```

### Expected Performance/Maintainability Gains

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| File size (live.py) | 1,430 LOC | ~150 LOC | 90% reduction |
| Cognitive load | 5 collectors in one file | 1 collector per file | Easier to reason about |
| Testability | Hard to test individual collectors | Can unit-test each collector in isolation | Better test coverage |
| Parallel development | Merge conflicts on live.py | Developers can work on different collectors simultaneously | Faster iteration |
| Error isolation | One collector error affects parsing of others | Physical separation prevents cross-contamination | More robust |

### Risk Assessment

**Possible Side Effects**:
1. **Import cycles**: Ensure `collectors/__init__.py` doesn't import from `live.py`
2. **Config dependencies**: Collectors import `SSE_*_INTERVAL_MS` from `dashboard.config` — verify no circular imports
3. **Type hints**: `_parse_proc_stat()` returns `List[Optional[dict]]` — ensure type consistency across module boundaries

**Test Coverage Needed**:
1. Unit tests for each collector's `collect()` method (mock sysfs reads)
2. Integration test: `LiveMonitor` starts/stops all collectors correctly
3. Regression test: SSE endpoint still produces identical JSON structure
4. Edge case tests: missing sysfs files, offline CPUs, thermal zone failures

**Migration Strategy**:
1. Create `collectors/` directory with `__init__.py`
2. Extract `base.py` first (no dependencies)
3. Extract one collector at a time, run tests after each
4. Update imports in `live.py` after all collectors are moved
5. Run full test suite before committing

---

## Module 2: `dashboard/services/network.py`

### Current State Summary

- **Lines of Code**: 1,006
- **Cyclomatic Complexity**: 266
- **Weighted Score**: 267,596
- **Optimization Category**: **Refactor**

**Key Hotspots**:
1. `get_wifi_info()` (lines 402–638): **237 lines** with 5 sequential tool attempts (nmcli → iwconfig → iw → /proc/net/wireless → rfkill)
2. `get_ip_addresses()` (lines 109–400): **292 lines** with nested conditionals for interface classification (loopback, wireless, bridge, virtual, cellular)
3. `get_dns_info()` (lines 693–812): **120 lines** with 4 fallback sources (systemd-resolved → nmcli → resolv.conf → fallback)
4. `format_bytes()` and `get_known_dns_provider()` are utility functions that could be standalone
5. Heavy use of regex parsing inline (e.g., `re.split(r"(?<!\\):", line)` for nmcli output)

**Structural Issues**:
- Functions embed raw CLI parsing logic directly (no separation between "fetch" and "parse")
- No dataclasses for structured responses — returns raw dicts with inconsistent keys
- Repeated pattern: try tool A, if fails try tool B, if fails try tool C (could be strategy pattern)
- Line 374: nested `sort_key()` function inside `get_ip_addresses()` — extract to module level

### Proposed Refactoring Steps

#### Step 1: Create Dataclasses for Structured Responses
```python
# dashboard/services/network_models.py (new file)

from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class InterfaceAddress:
    """Single IP address on an interface."""
    address: str
    netmask: Optional[str] = None
    prefix: Optional[int] = None
    family: str = "inet"  # inet, inet6

@dataclass
class NetworkInterface:
    """Network interface with full details."""
    name: str
    category: str  # ethernet, wireless, loopback, bridge, virtual, cellular
    is_up: bool = False
    is_default: bool = False
    mac: Optional[str] = None
    mtu: Optional[int] = None
    addresses: List[InterfaceAddress] = field(default_factory=list)
    rx_bytes: int = 0
    tx_bytes: int = 0
    rx_packets: int = 0
    tx_packets: int = 0
    driver: Optional[str] = None
    message: Optional[str] = None  # Error message if fetch failed

@dataclass
class WiFiConnection:
    """Active WiFi connection details."""
    interface: str
    ssid: str
    bssid: str
    signal_percent: int
    signal_dbm: Optional[int] = None
    frequency_mhz: Optional[int] = None
    channel: Optional[int] = None
    bitrate: Optional[str] = None
    tx_power: Optional[str] = None
    security: Optional[str] = None
    mode: str = "Infrastructure"
    driver: Optional[str] = None

@dataclass
class DNSServer:
    """DNS server with metadata."""
    address: str
    source: str  # systemd-resolved, nmcli, resolv.conf, fallback
    provider: Optional[str] = None  # Cloudflare, Google, Quad9, etc.
    is_local_stub: bool = False
```

#### Step 2: Extract Parsing Logic into Helper Functions
**Before** (inline in `get_wifi_info()`):
```python
for line in out.splitlines():
    parts = re.split(r"(?<!\\):", line)
    if len(parts) >= 8:
        is_active = parts[0].strip().lower() == "yes"
        raw_ssid = parts[1].replace(r"\:", ":").strip()
        # ... 20 more lines of parsing
```

**After** (extracted):
```python
def _parse_nmcli_wifi_line(line: str) -> Optional[dict]:
    """Parse single nmcli WiFi scan line into structured dict."""
    parts = re.split(r"(?<!\\):", line)
    if len(parts) < 8:
        return None

    return {
        "is_active": parts[0].strip().lower() == "yes",
        "ssid": parts[1].replace(r"\:", ":").strip() or "<Hidden SSID>",
        "bssid": parts[2].replace(r"\:", ":").strip(),
        "mode": parts[3].strip(),
        "channel": parts[4].strip(),
        "frequency": parts[5].strip(),
        "rate": parts[6].strip(),
        "signal": int(parts[7]) if parts[7].isdigit() else 0,
        "security": parts[8].strip() if len(parts) > 8 else "Open",
    }
```

#### Step 3: Refactor `get_wifi_info()` Using Strategy Pattern
**Current structure** (237 lines of sequential fallbacks):
```python
def get_wifi_info() -> dict:
    # 1. Try nmcli (60 lines)
    # 2. Try iwconfig (50 lines)
    # 3. Try iw (40 lines)
    # 4. Try /proc/net/wireless (20 lines)
    # 5. Check rfkill (10 lines)
    # Return aggregated dict
```

**Refactored structure**:
```python
class WiFiInfoProvider(Protocol):
    """Protocol for WiFi info sources."""
    def is_available(self) -> bool: ...
    def get_connection(self, interface: str) -> Optional[WiFiConnection]: ...
    def scan_networks(self, interface: str) -> List[WiFiConnection]: ...

class NmcliProvider: ...
class IwconfigProvider: ...
class IwProvider: ...
class ProcWirelessProvider: ...

def get_wifi_info() -> dict:
    providers: List[WiFiInfoProvider] = [
        NmcliProvider(),
        IwconfigProvider(),
        IwProvider(),
        ProcWirelessProvider(),
    ]

    for provider in providers:
        if provider.is_available():
            result = provider.get_connection(primary_iface)
            if result:
                return result.to_dict()

    return {"has_hardware": False, "message": "No WiFi connection"}
```

#### Step 4: Group Related Functions into Submodules
**Proposed structure**:
```
dashboard/services/
├── network.py              # Keep only public API functions
├── network/
│   ├── __init__.py
│   ├── interfaces.py       # get_ip_addresses(), get_gateways(), _parse_* helpers
│   ├── wifi.py             # get_wifi_info(), scan_wifi_networks(), WiFi providers
│   ├── dns.py              # get_dns_info(), get_dns_servers(), dns_lookup()
│   ├── diagnostics.py      # ping_test(), get_network_summary()
│   └── utils.py            # format_bytes(), get_known_dns_provider()
```

**Example: `network/wifi.py`**:
```python
"""WiFi information providers."""

import os
import re
from typing import List, Optional
from dashboard.dependencies import run_command, which
from ..network_models import WiFiConnection

def get_wifi_info() -> dict:
    """Get comprehensive WiFi information."""
    # 1. Detect wireless interfaces
    # 2. Try each provider in priority order
    # 3. Return aggregated result
    ...

def scan_wifi_networks() -> List[dict]:
    """Trigger active WiFi scan."""
    # Use nmcli if available, fallback to iw
    ...
```

#### Step 5: Replace Nested Conditionals with Guard Clauses
**Before** (in `get_ip_addresses()`):
```python
for item in raw_list:
    name = item.get("ifname", "")
    if not name:
        continue

    cat = "ethernet"
    is_loopback = name == "lo" or item.get("link_type") == "loopback"
    is_wireless = os.path.exists(f"/sys/class/net/{name}/wireless") or ...
    is_bridge = os.path.exists(f"/sys/class/net/{name}/bridge") or ...
    is_virtual = name.startswith(("veth", "tun", "tap", "wg", "dummy"))
    is_cellular = name.startswith(("wwan", "rmnet", "cdc-wdm"))

    if is_loopback:
        cat = "loopback"
    elif is_wireless:
        cat = "wireless"
    elif is_bridge:
        cat = "bridge"
    # ... more elif
```

**After**:
```python
def _classify_interface(name: str, item: dict) -> str:
    """Classify network interface into category."""
    if name == "lo" or item.get("link_type") == "loopback":
        return "loopback"
    if _is_wireless(name):
        return "wireless"
    if _is_bridge(name):
        return "bridge"
    if _is_cellular(name):
        return "cellular"
    if _is_virtual(name):
        return "virtual"
    return "ethernet"

def _is_wireless(name: str) -> bool:
    return (
        os.path.exists(f"/sys/class/net/{name}/wireless")
        or os.path.exists(f"/sys/class/net/{name}/phy80211")
        or name.startswith(("wlan", "wlp", "wlo", "ra"))
    )
```

### Expected Performance/Maintainability Gains

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Function size (`get_wifi_info`) | 237 lines | ~50 lines (orchestration only) | 80% reduction |
| Parsing logic | Inline in functions | Extracted helpers with unit tests | Easier to test |
| Type safety | Raw dicts with inconsistent keys | Dataclasses with type hints | Fewer runtime errors |
| Extensibility | Adding new tool requires editing 200-line function | Implement `WiFiInfoProvider` protocol | Open/closed principle |
| Readability | Nested conditionals | Guard clauses + single-responsibility functions | Easier to understand |

### Risk Assessment

**Possible Side Effects**:
1. **API compatibility**: Existing callers expect specific dict keys — ensure dataclasses serialize identically
2. **Performance**: Strategy pattern adds slight overhead (negligible for CLI tools)
3. **Error handling**: Current code swallows exceptions silently — maintain this behavior for backward compatibility

**Test Coverage Needed**:
1. Unit tests for each parsing helper (`_parse_nmcli_wifi_line`, `_classify_interface`, etc.)
2. Integration tests: mock `run_command` and verify correct tool selection
3. Regression tests: verify output structure matches existing API
4. Edge cases: no wireless hardware, all tools unavailable, malformed CLI output

**Migration Strategy**:
1. Create `network_models.py` with dataclasses (no breaking changes)
2. Extract utility functions to `network/utils.py`
3. Refactor one function at a time (start with `get_dns_info` — smallest)
4. Run existing tests after each refactoring
5. Update type hints incrementally

---

## Module 3: `tests/unit/test_packages.py`

### Current State Summary

- **Lines of Code**: 388
- **Cyclomatic Complexity**: 172
- **Weighted Score**: 66,736
- **Optimization Category**: **Refactor**

**Key Hotspots**:
1. 8 test classes (`TestBasePackageManager`, `TestNullPackageManager`, `TestApkManager`, `TestAptManager`, `TestPacmanManager`, `TestDnfManager`, `TestPackageManagerFunctions`, `TestCacheBehavior`)
2. Repetitive `@patch("dashboard.services.packages.run_command")` decorators on nearly every test method
3. Similar setUp patterns: each test creates a manager instance and mocks `run_command` with different return values
4. Test methods are small (5–15 lines) but there are many of them (40+ tests)
5. No parameterization: each package manager (apk, apt, pacman, dnf) has separate test classes with nearly identical tests

**Structural Issues**:
- Repetitive mock setup: `mock_run.return_value = (0, "output", "")` appears 20+ times
- No fixtures: `run_command` mock is recreated for each test method
- No parameterization: `test_get_installed_packages_parses_output` is duplicated for each manager
- Single file for all package manager tests — hard to navigate when adding new managers

### Proposed Refactoring Steps

#### Step 1: Create Pytest Fixtures for Common Mocks
**New file**: `tests/unit/conftest.py` (or add to existing)
```python
"""Shared fixtures for unit tests."""

import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_run_command(mocker):
    """Mock run_command with default successful return."""
    mock = mocker.patch("dashboard.services.packages.run_command")
    mock.return_value = (0, "", "")
    return mock

@pytest.fixture
def mock_run_command_failure(mocker):
    """Mock run_command to simulate failure."""
    mock = mocker.patch("dashboard.services.packages.run_command")
    mock.return_value = (1, "", "command failed")
    return mock

@pytest.fixture
def mock_path_exists(mocker):
    """Mock os.path.exists for availability checks."""
    return mocker.patch("dashboard.services.packages.os.path.exists")
```

#### Step 2: Parameterize Package Manager Tests
**Before** (separate test classes):
```python
class TestApkManager:
    def test_get_install_command(self):
        mgr = ApkManager()
        assert mgr.get_install_command("htop") == ["apk", "add", "htop"]

class TestAptManager:
    def test_get_install_command(self):
        mgr = AptManager()
        assert mgr.get_install_command("htop") == ["apt-get", "install", "-y", "htop"]

# ... repeated for PacmanManager, DnfManager
```

**After** (parameterized):
```python
import pytest
from dashboard.services.packages import ApkManager, AptManager, PacmanManager, DnfManager

@pytest.mark.parametrize("manager_class,package,expected_command", [
    pytest.param(ApkManager, "htop", ["apk", "add", "htop"], id="apk"),
    pytest.param(AptManager, "htop", ["apt-get", "install", "-y", "htop"], id="apt"),
    pytest.param(PacmanManager, "htop", ["pacman", "-S", "--noconfirm", "htop"], id="pacman"),
    pytest.param(DnfManager, "htop", ["dnf", "install", "-y", "htop"], id="dnf"),
])
def test_get_install_command(manager_class, package, expected_command):
    mgr = manager_class()
    assert mgr.get_install_command(package) == expected_command
```

#### Step 3: Split into Per-Manager Test Files
**Proposed structure**:
```
tests/unit/
├── test_packages/
│   ├── __init__.py
│   ├── conftest.py           # Shared fixtures for package tests
│   ├── test_base.py          # TestBasePackageManager, TestNullPackageManager
│   ├── test_apk.py           # TestApkManager
│   ├── test_apt.py           # TestAptManager
│   ├── test_pacman.py        # TestPacmanManager
│   ├── test_dnf.py           # TestDnfManager
│   └── test_functions.py     # TestPackageManagerFunctions (module-level functions)
```

**Example: `test_packages/test_apk.py`**:
```python
"""Tests for ApkManager."""

import pytest
from dashboard.services.packages import ApkManager

class TestApkManager:
    def test_id_attribute(self):
        mgr = ApkManager()
        assert mgr.id == "apk"

    def test_is_available_when_apk_exists(self, mock_path_exists):
        mock_path_exists.return_value = True
        mgr = ApkManager()
        assert mgr.is_available() is True

    @pytest.mark.parametrize("command_name,expected", [
        ("add", ["apk", "add"]),
        ("upgrade", ["apk", "upgrade"]),
    ])
    def test_get_base_command(self, command_name, expected):
        mgr = ApkManager()
        result = mgr._get_base_command(command_name)
        assert result == expected

    def test_get_installed_packages_parses_v_output(self, mock_run_command):
        mock_run_command.return_value = (0, "musl-1.2.4-r0\nbusybox-1.36.1-r2\n", "")
        mgr = ApkManager()
        pkgs = mgr.get_installed_packages()

        assert len(pkgs) == 2
        assert pkgs[0]["name"] == "busybox"
        assert pkgs[0]["version"] == "1.36.1-r2"
```

#### Step 4: Use `pytest.fixture` for Test Data
**Before**:
```python
def test_get_installed_packages_parses_output(self, mock_run):
    mock_run.return_value = (0, "musl-1.2.4-r0\nbusybox-1.36.1-r2\n", "")
    # ... test logic
```

**After**:
```python
@pytest.fixture
def apk_installed_packages_output():
    return (0, "musl-1.2.4-r0\nbusybox-1.36.1-r2\n", "")

def test_get_installed_packages_parses_output(self, mock_run_command, apk_installed_packages_output):
    mock_run_command.return_value = apk_installed_packages_output
    # ... test logic
```

#### Step 5: Add Test Coverage for Edge Cases
Current tests cover happy paths but miss:
- Malformed CLI output (e.g., `apk` output with missing version)
- Timeout scenarios (`run_command` raises `TimeoutExpired`)
- Unicode package names/descriptions
- Empty output (package manager returns no results)

**Example edge case test**:
```python
def test_get_installed_packages_handles_malformed_output(self, mock_run_command):
    """Test parsing when output doesn't match expected format."""
    mock_run_command.return_value = (0, "invalid-line-no-dash\nanother-bad-line\n", "")
    mgr = ApkManager()
    pkgs = mgr.get_installed_packages()
    # Should handle gracefully, not crash
    assert isinstance(pkgs, list)
```

### Expected Performance/Maintainability Gains

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Test file count | 1 file (388 LOC) | 7 files (~50 LOC each) | Easier to navigate |
| Code duplication | 40% (repeated mock setup) | <10% (fixtures + parameterization) | DRY principle |
| Test discovery | Must read entire file to find specific manager tests | One file per manager | Faster onboarding |
| Adding new manager | Edit existing test class (risk of breaking others) | Create new test file | Isolated changes |
| Mock setup | Repeated in every test method | Centralized in fixtures | Less boilerplate |

### Risk Assessment

**Possible Side Effects**:
1. **Fixture scope**: Ensure `mock_run_command` fixture has correct scope (function vs module)
2. **Import paths**: Splitting files requires updating imports — use `tests/unit/test_packages/__init__.py` to re-export if needed
3. **Test discovery**: pytest should auto-discover `test_*.py` files in subdirectories — verify with `pytest --collect-only`

**Test Coverage Needed**:
1. Run existing test suite before refactoring (capture baseline)
2. Run after each file split to ensure no regressions
3. Add edge case tests for malformed output, timeouts, unicode

**Migration Strategy**:
1. Create `tests/unit/test_packages/` directory with `__init__.py`
2. Add `conftest.py` with shared fixtures
3. Extract `test_base.py` first (simplest, no mocks)
4. Parameterize and extract one manager at a time
5. Run `pytest tests/unit/test_packages/` after each extraction
6. Delete old `test_packages.py` after all tests are migrated

---

## Implementation Priority

1. **Start with `test_packages.py`** (easiest, lowest risk, immediate maintainability gains)
2. **Then `network.py`** (medium complexity, refactoring only — no physical decomposition required initially)
3. **Finally `live.py`** (most complex, requires careful import management and test verification)

## Verification Checklist

Before marking this task complete:

- [ ] `plan.md` saved in workspace root
- [ ] Each module has: current state, refactoring steps, expected gains, risk assessment, code examples
- [ ] Plan is specific enough to implement without clarification (file paths, function names, line numbers)
- [ ] Migration strategies include test verification steps
- [ ] Edge cases and potential side effects are documented

---

**Next Task**: t_011cfa17 — Create GitHub issues from this optimization plan
