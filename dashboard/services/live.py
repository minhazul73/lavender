"""
SSE Live Monitoring — per-metric collectors with independent timers,
rolling buffers, and lazy start/stop.

Each metric (CPU freq, RAM, thermal zones, battery, network rate)
has its own collector that polls at its own interval, stores the last N
datapoints in a rolling buffer (for sparklines), starts only when a client
subscribes, and stops when the last client unsubscribes.
"""
import asyncio
import os
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional

from dashboard.config import (
    SSE_CPU_BUFFER,
    SSE_CPU_POLL_INTERVAL,
    SSE_RAM_BUFFER,
    SSE_RAM_POLL_INTERVAL,
    SSE_THERMAL_BUFFER,
    SSE_THERMAL_POLL_INTERVAL,
    SSE_BATTERY_BUFFER,
    SSE_BATTERY_POLL_INTERVAL,
    SSE_NETWORK_BUFFER,
    SSE_NETWORK_POLL_INTERVAL,
)


# ============================================================
# Rolling buffer
# ============================================================

class RingBuffer:
    """Fixed-size ring buffer for sparkline datapoints."""

    def __init__(self, capacity: int):
        self.capacity = capacity
        self._data: Deque[Any] = deque(maxlen=capacity)

    def push(self, value: Any) -> None:
        self._data.append(value)

    def all(self) -> List[Any]:
        return list(self._data)

    def latest(self) -> Any:
        if not self._data:
            return None
        return self._data[-1]

    def __len__(self) -> int:
        return len(self._data)

    def __bool__(self) -> bool:
        return bool(self._data)


# ============================================================
# Per-metric collector with lazy start/stop
# ============================================================

class MetricCollector:
    """
    Wraps a data-fetching function with a background timer.

    - Starts polling when the first subscriber attaches.
    - Stops polling when the last subscriber detaches.
    - Pushes new values to all subscribers as they arrive.
    - Maintains a rolling buffer for sparkline rendering.
    """

    def __init__(
        self,
        name: str,
        poll_interval_ms: int,
        buffer_size: int,
        fetch_fn: Callable[[], Any],
    ):
        self.name = name
        self.poll_interval_ms = poll_interval_ms
        self.buffer = RingBuffer(buffer_size)
        self._fetch_fn = fetch_fn
        self._subs: List[Callable[[Any], None]] = []
        self._task: Optional[asyncio.Task[None]] = None
        self._running = False

    def subscribe(self, callback: Callable[[Any], None]) -> None:
        """Add a subscriber. Starts polling if not already running."""
        if callback not in self._subs:
            self._subs.append(callback)
        if not self._running:
            self._start()

    def unsubscribe(self, callback: Callable[[Any], None]) -> None:
        """Remove a subscriber. Stops polling if no subscribers left."""
        if callback in self._subs:
            self._subs.remove(callback)
        if not self._subs and self._running:
            self._stop()

    def _start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())

    def _stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    async def _poll_loop(self) -> None:
        """Background loop: fetch data, push to subs, sleep."""
        while self._running:
            try:
                value = self._fetch_fn()
                self.buffer.push(value)
                for sub in list(self._subs):
                    try:
                        sub(value)
                    except Exception:
                        pass
            except Exception:
                pass
            await asyncio.sleep(self.poll_interval_ms / 1000.0)


# ============================================================
# Data fetch functions (sysfs / /proc reads, no subprocess)
# ============================================================

def _read_sysfs_int(path: str) -> Optional[int]:
    """Read a single sysfs file and return as int, or None on failure."""
    try:
        with open(path, "r") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def _read_cpu_freqs() -> Dict[str, Any]:
    """
    Read per-core CPU frequency from sysfs.
    Returns: { cpus: [{core, frequency_mhz, frequency_khz, governor, min_freq, max_freq}], count }
    """
    cpus = []
    cpu_dir = "/sys/devices/system/cpu"
    try:
        for entry in sorted(os.listdir(cpu_dir)):
            if not entry.startswith("cpu") or not entry[3:].isdigit():
                continue
            core_path = os.path.join(cpu_dir, entry, "cpufreq")
            if not os.path.isdir(core_path):
                continue
            cur_freq = _read_sysfs_int(os.path.join(core_path, "scaling_cur_freq"))
            min_freq = _read_sysfs_int(os.path.join(core_path, "scaling_min_freq"))
            max_freq = _read_sysfs_int(os.path.join(core_path, "scaling_max_freq"))
            gov_path = os.path.join(core_path, "scaling_governor")
            try:
                with open(gov_path) as f:
                    governor = f.read().strip()
            except OSError:
                governor = None
            freq_mhz = (cur_freq / 1000.0) if cur_freq is not None else None
            cpus.append({
                "core": int(entry[3:]),
                "frequency_khz": cur_freq,
                "frequency_mhz": freq_mhz,
                "min_freq": min_freq,
                "max_freq": max_freq,
                "governor": governor,
            })
    except OSError:
        pass
    return {"cpus": cpus, "count": len(cpus)}


def _read_ram() -> Dict[str, Any]:
    """
    Read /proc/meminfo and return parsed memory info.
    All values in kB unless noted.
    Returns: { total, free, available, used, buffers, cached, swap_total, swap_free, swap_used, used_pct }
    """
    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
    except OSError:
        return {"error": "Cannot read /proc/meminfo"}

    info: Dict[str, int] = {}
    for line in lines:
        parts = line.split(":")
        if len(parts) != 2:
            continue
        key = parts[0].strip()
        try:
            val = int(parts[1].strip().split()[0])
        except (ValueError, IndexError):
            continue
        info[key] = val

    total = info.get("MemTotal", 0)
    free = info.get("MemFree", 0)
    avail = info.get("MemAvailable", free)
    used = max(0, total - avail)
    buffers = info.get("Buffers", 0)
    cached = info.get("Cached", 0) + info.get("SReclaimable", 0)
    swap_total = info.get("SwapTotal", 0)
    swap_free = info.get("SwapFree", 0)
    swap_used = max(0, swap_total - swap_free)

    used_pct = round((used / total * 100), 1) if total > 0 else 0.0

    return {
        "total": total,
        "free": free,
        "available": avail,
        "used": used,
        "buffers": buffers,
        "cached": cached,
        "swap_total": swap_total,
        "swap_free": swap_free,
        "swap_used": swap_used,
        "used_pct": used_pct,
    }


def _read_thermal_zones() -> List[Dict[str, Any]]:
    """
    Read all thermal zones from /sys/class/thermal/.
    Returns a list of {name, type, temp_celsius, temp_millicelsius, warning}.
    """
    zones: List[Dict[str, Any]] = []
    thermal_dir = "/sys/class/thermal"
    try:
        for entry in sorted(os.listdir(thermal_dir)):
            if not entry.startswith("thermal_zone"):
                continue
            zone_dir = os.path.join(thermal_dir, entry)
            temp_path = os.path.join(zone_dir, "temp")
            type_path = os.path.join(zone_dir, "type")
            name_path = os.path.join(zone_dir, "thermal_zone_name")

            temp_milli = _read_sysfs_int(temp_path)
            temp_c = (temp_milli / 1000.0) if temp_milli is not None else None

            zone_type = None
            zone_name = None
            try:
                with open(type_path) as f:
                    zone_type = f.read().strip()
            except OSError:
                pass
            try:
                with open(name_path) as f:
                    zone_name = f.read().strip()
            except OSError:
                pass

            label = zone_name or zone_type or entry
            warn = temp_c is not None and temp_c >= 70.0

            zones.append({
                "name": label,
                "type": zone_type,
                "temp_millicelsius": temp_milli,
                "temp_celsius": temp_c,
                "warning": warn,
            })
    except OSError:
        pass
    return zones


def _read_battery() -> Dict[str, Any]:
    """
    Lightweight battery read for SSE updates.
    Reuses the same logic as the full battery endpoint but returns
    only the fields needed for the overview.
    """
    try:
        from dashboard.services.battery import get_battery_info
        info = get_battery_info()
        return {
            "percentage": info.get("percentage"),
            "state": info.get("state"),
            "temperature": info.get("temperature"),
            "voltage": info.get("voltage"),
            "energy_rate": info.get("energy_rate"),
            "time_to_full": info.get("time_to_full"),
            "time_to_empty": info.get("time_to_empty"),
            "charging": info.get("charging"),
        }
    except Exception:
        return {"error": "Battery read failed"}


# Network rate state — persists between calls
_network_state: Dict[str, Any] = {"rx_bytes": 0, "tx_bytes": 0, "timestamp": 0.0}


def _read_network_rate() -> Dict[str, Any]:
    """
    Read network interface rates via sysfs delta.
    Reads rx_bytes/tx_bytes from /sys/class/net/<iface>/statistics/,
    computes bytes/sec since last read.
    Returns: { iface, rx_rate_bps, tx_rate_bps, timestamp }
    """
    global _network_state

    result: Dict[str, Any] = {"iface": None, "rx_rate_bps": 0, "tx_rate_bps": 0}

    net_dir = "/sys/class/net"
    try:
        ifaces = sorted(os.listdir(net_dir))
    except OSError:
        return {"error": "Cannot read /sys/class/net"}

    # Find the first non-loopback interface with statistics
    target_iface = None
    for iface in ifaces:
        if iface == "lo":
            continue
        stats_dir = os.path.join(net_dir, iface, "statistics")
        if not os.path.isdir(stats_dir):
            continue
        target_iface = iface
        break

    if target_iface is None:
        target_iface = "lo"

    stats_dir = os.path.join(net_dir, target_iface, "statistics")
    rx = _read_sysfs_int(os.path.join(stats_dir, "rx_bytes"))
    tx = _read_sysfs_int(os.path.join(stats_dir, "tx_bytes"))

    if rx is None or tx is None:
        return {"error": f"Cannot read stats for {target_iface}"}

    result["iface"] = target_iface

    now = time.time()
    prev = _network_state
    dt = now - prev.get("timestamp", 0)
    if dt > 0 and prev.get("rx_bytes", 0) > 0:
        result["rx_rate_bps"] = (rx - prev["rx_bytes"]) * 8 / dt
        result["tx_rate_bps"] = (tx - prev["tx_bytes"]) * 8 / dt

    _network_state = {"rx_bytes": rx, "tx_bytes": tx, "timestamp": now}
    return result


# ============================================================
# Collector registry
# ============================================================

class LiveMonitor:
    """
    Owns all metric collectors. Provides subscribe/unsubscribe for SSE.
    Lazy: collectors start on first subscribe, stop on last unsubscribe.
    """

    def __init__(self):
        self._cpu = MetricCollector(
            "cpu",
            SSE_CPU_POLL_INTERVAL,
            SSE_CPU_BUFFER,
            _read_cpu_freqs,
        )
        self._ram = MetricCollector(
            "ram",
            SSE_RAM_POLL_INTERVAL,
            SSE_RAM_BUFFER,
            _read_ram,
        )
        self._thermal = MetricCollector(
            "thermal",
            SSE_THERMAL_POLL_INTERVAL,
            SSE_THERMAL_BUFFER,
            _read_thermal_zones,
        )
        self._battery = MetricCollector(
            "battery",
            SSE_BATTERY_POLL_INTERVAL,
            SSE_BATTERY_BUFFER,
            _read_battery,
        )
        self._network = MetricCollector(
            "network",
            SSE_NETWORK_POLL_INTERVAL,
            SSE_NETWORK_BUFFER,
            _read_network_rate,
        )

    def subscribe(self, metric: str, callback: Callable[[Any], None]) -> None:
        collectors = {
            "cpu": self._cpu,
            "ram": self._ram,
            "thermal": self._thermal,
            "battery": self._battery,
            "network": self._network,
        }
        collector = collectors.get(metric)
        if collector:
            collector.subscribe(callback)

    def unsubscribe(self, metric: str, callback: Callable[[Any], None]) -> None:
        collectors = {
            "cpu": self._cpu,
            "ram": self._ram,
            "thermal": self._thermal,
            "battery": self._battery,
            "network": self._network,
        }
        collector = collectors.get(metric)
        if collector:
            collector.unsubscribe(callback)

    def get_buffer(self, metric: str) -> RingBuffer:
        """Get the rolling buffer for a metric (for initial sparkline render)."""
        buffers = {
            "cpu": self._cpu.buffer,
            "ram": self._ram.buffer,
            "thermal": self._thermal.buffer,
            "battery": self._battery.buffer,
            "network": self._network.buffer,
        }
        return buffers.get(metric, RingBuffer(0))

    def get_latest(self, metric: str) -> Any:
        """Get the latest value for a metric."""
        collectors = {
            "cpu": self._cpu,
            "ram": self._ram,
            "thermal": self._thermal,
            "battery": self._battery,
            "network": self._network,
        }
        collector = collectors.get(metric)
        if collector:
            return collector.buffer.latest()
        return None


# Singleton — one monitor for the whole process
_live_monitor: Optional[LiveMonitor] = None


def get_live_monitor() -> LiveMonitor:
    global _live_monitor
    if _live_monitor is None:
        _live_monitor = LiveMonitor()
    return _live_monitor
