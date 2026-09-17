"""
Per-metric collector base class and individual collectors.

CPU freq: reads /sys/devices/system/cpu/*/cpufreq/scaling_cur_freq
RAM: reads /proc/meminfo once followed by /proc/stat for used calculation
Thermal: reads hwmonpad-ec-thermal via sysfs
Battery: reads /sys/class/power_supply/*/capacity + /sys/bus/platform/devices/*/...
Network: reads sysfs net/dev for interface counters, calculates delta
Power draw: optional, reads from battery energy_rate if available
"""

from __future__ import annotations

import asyncio
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from dashboard.config import (
    SSE_THERMAL_INTERVAL_MS,
    SSE_NETWORK_INTERVAL_MS,
    SSE_CPU_INTERVAL_MS,
    SSE_RAM_INTERVAL_MS,
    SSE_BATTERY_INTERVAL_MS,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _read_file(path: str) -> Optional[str]:
    """Read a single sysfs/proc file, return None on any failure."""
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except (FileNotFoundError, PermissionError, OSError):
        return None


def _read_int(path: str, default: int = 0) -> int:
    s = _read_file(path)
    if s is None:
        return default
    try:
        return int(s)
    except ValueError:
        return default


def _read_float(path: str, default: float = 0.0) -> float:
    s = _read_file(path)
    if s is None:
        return default
    try:
        return float(s)
    except ValueError:
        return default


def _get_loadavg(index: int) -> float:
    """Read a specific load average from /proc/loadavg (0=1min, 1=5min, 2=15min)."""
    text = _read_file("/proc/loadavg")
    if text is None:
        return 0.0
    parts = text.strip().split()
    if len(parts) > index:
        try:
            return float(parts[index])
        except ValueError:
            return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Ring buffer (memory-efficient, fixed-window history)
# ---------------------------------------------------------------------------

class RingBuffer:
    """Fixed-size circular buffer for a single metric stream.

    Reads are lock-free (only append from one asyncio task, read from any).
    We don't need a lock because appends only happen in the collector loop
    which is single-threaded per metric; reads happen on main thread during
    HTTP response generation.
    """

    __slots__ = ("_buf", "_size")

    def __init__(self, size: int) -> None:
        self._buf: deque = deque(maxlen=size)
        self._size = size

    def __len__(self) -> int:
        return len(self._buf)

    def append(self, value: float) -> None:
        self._buf.append(value)

    def __iter__(self):
        return iter(self._buf)

    def values(self) -> List[float]:
        return list(self._buf)

    @property
    def is_empty(self) -> bool:
        return len(self._buf) == 0


# ---------------------------------------------------------------------------
# Collector protocol
# ---------------------------------------------------------------------------

@dataclass
class CollectorStats:
    """Running stats for a single collector."""
    sample_count: int = 0
    last_error: Optional[str] = None
    errors_in_row: int = 0


class MetricCollector:
    """Base class for a single-metric SSE collector.

    Subclasses implement:
      - collect() -> dict   (the current metric sample)
      - get_buffer()        (RingBuffer for sparkline/history)

    The base handles:
      - periodic collection loop
      - error backoff
      - buffer management
    """

    __slots__ = ("_interval_ms", "_buffer", "_stats", "_stop_event",
                 "_task", "_buffer_key")

    def __init__(self, interval_ms: int, history_size: int,
                 buffer_key: str) -> None:
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
                # Don't crash the whole SSE engine on a single collector
                # failure — log and continue after a brief pause.
                await asyncio.sleep(min(interval_s, 1.0))
            await asyncio.sleep(interval_s)

    def _on_sample(self, sample: dict) -> None:
        """Called for each successful sample. Subclasses may override."""
        pass

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        if self._task is not None and not self._task.done():
            return  # already running
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


# ---------------------------------------------------------------------------
# Per-core CPU usage from /proc/stat
# ---------------------------------------------------------------------------

def _parse_proc_stat() -> List[Optional[dict]]:
    """Parse /proc/stat and return per-core CPU time dicts.

    Each dict contains: user, nice, system, idle, iowait, irq, softirq,
    steal, guest, guestnice, total.

    Returns a list indexed by cpu number; None for offline/missing cores.
    """
    text = _read_file("/proc/stat")
    if text is None:
        return []

    # Find max core number to size the list
    max_core = -1
    for line in text.splitlines():
        if line.startswith("cpu") and not line.startswith("cpu "):
            try:
                num = int(line.split()[0][3:])
                max_core = max(max_core, num)
            except (ValueError, IndexError):
                pass

    if max_core < 0:
        return []

    cpus: List[Optional[dict]] = [None] * (max_core + 1)

    for line in text.splitlines():
        if line.startswith("cpu") and not line.startswith("cpu "):
            parts = line.split()
            try:
                core_num = int(parts[0][3:])
            except (ValueError, IndexError):
                continue
            values = []
            for p in parts[1:]:
                try:
                    values.append(int(p))
                except ValueError:
                    values.append(0)
            # Pad to 10 fields (user, nice, system, idle, iowait, irq,
            # softirq, steal, guest, guestnice)
            while len(values) < 10:
                values.append(0)

            user, nice, system, idle, iowait, irq, softirq, steal, guest, guestnice = values[:10]
            # Guest time is already in usertime, subtract to avoid double-counting
            user -= guest
            nice -= guestnice

            total = user + nice + system + idle + iowait + irq + softirq + steal + guest + guestnice
            idle_total = idle + iowait

            cpus[core_num] = {
                "user": user, "nice": nice, "system": system,
                "idle": idle, "iowait": iowait, "irq": irq,
                "softirq": softirq, "steal": steal, "guest": guest,
                "guestnice": guestnice, "total": total,
                "idle_total": idle_total,
            }

    return cpus


def _calc_cpu_usage(prev: Optional[dict], curr: Optional[dict]) -> Optional[float]:
    """Calculate CPU usage percentage between two samples.

    Returns None if either sample is missing.
    """
    if prev is None or curr is None:
        return None
    total_delta = curr["total"] - prev["total"]
    if total_delta <= 0:
        return 0.0
    idle_delta = curr["idle_total"] - prev["idle_total"]
    return (total_delta - idle_delta) / total_delta * 100.0


# ---------------------------------------------------------------------------
# CPU Frequency Collector
# ---------------------------------------------------------------------------

@dataclass
class CPUCoreInfo:
    core: int
    frequency_mhz: Optional[float] = None   # None if cpufreq not exposed
    governor: Optional[str] = None
    capacity: Optional[int] = None          # scheduler capacity (big vs little)


class CPUFreqCollector(MetricCollector):
    """Collects per-core CPU frequency from sysfs and per-core usage from /proc/stat.

    Falls back to count-only if cpufreq sysfs is unavailable (e.g. some
    ARM SoCs without dynamic frequency scaling).
    """

    __slots__ = ("_cpu_dir", "_cpus", "_cpus_last_update", "_interval_ms",
                 "_buffer", "_stats", "_stop_event", "_task", "_has_cpufreq",
                 "_prev_stat", "_curr_stat")

    def __init__(self, interval_ms: int = SSE_CPU_INTERVAL_MS,
                 history_size: int = 20) -> None:
        super().__init__(interval_ms, history_size, "cpu")
        self._cpu_dir = "/sys/devices/system/cpu"
        self._cpus: List[CPUCoreInfo] = []
        self._cpus_last_update = 0.0
        self._has_cpufreq = False
        self._prev_stat: List[Optional[dict]] = []
        self._curr_stat: List[Optional[dict]] = []

    async def collect(self) -> dict:
        """Return CPU info: count, per-core list (as plain dicts for JSON),
        first-core freq for sparkline, and per-core usage percentages."""
        now = time.monotonic()
        if now - self._cpus_last_update > 5.0:
            self._discover_cpus()

        cores = self._cpus
        if not cores:
            return {"cpus": [], "count": 0}

        cores_list = []
        for core in cores:
            freq_path = f"{self._cpu_dir}/cpu{core.core}/cpufreq/scaling_cur_freq"
            freq_khz = _read_int(freq_path, 0)
            freq_mhz = freq_khz / 1000.0 if freq_khz > 0 else None
            gov_path = f"{self._cpu_dir}/cpu{core.core}/cpufreq/scaling_governor"
            gov = _read_file(gov_path)
            cores_list.append({
                "cpu": core.core,
                "frequency_mhz": freq_mhz,
                "frequency_khz": freq_khz if freq_khz > 0 else None,
                "governor": gov if gov else None,
                "capacity": core.capacity,
            })

        freqs = [c["frequency_mhz"] for c in cores_list if c["frequency_mhz"] is not None]
        primary_freq = freqs[0] if freqs else None

        # Per-core CPU usage from /proc/stat
        self._prev_stat = self._curr_stat
        self._curr_stat = _parse_proc_stat()

        # First sample: no previous data, report 0%
        if not self._prev_stat:
            self._prev_stat = self._curr_stat

        per_core_usage = []
        for i, (prev, curr) in enumerate(zip(self._prev_stat, self._curr_stat)):
            usage = _calc_cpu_usage(prev, curr)
            per_core_usage.append({
                "core": i,
                "usage": round(usage, 1) if usage is not None else None,
            })

        return {
            "cpus": cores_list,
            "count": len(cores),
            "primary_frequency_mhz": primary_freq,
            # Lets the UI say "not supported by this kernel" instead of
            # rendering a permanently blank frequency readout.
            "cpufreq_available": self._has_cpufreq,
            "load1": _get_loadavg(0),
            "load5": _get_loadavg(1),
            "load15": _get_loadavg(2),
            "per_core_usage": per_core_usage,
        }

    def _discover_cpus(self) -> None:
        cpus = []
        if not os.path.isdir(self._cpu_dir):
            return
        has_cpufreq = False
        for entry in os.listdir(self._cpu_dir):
            if entry.startswith("cpu") and entry[3:].isdigit():
                core_num = int(entry[3:])
                online_path = f"{self._cpu_dir}/{entry}/online"
                online = _read_int(online_path, 1)
                if online:
                    if os.path.isdir(f"{self._cpu_dir}/{entry}/cpufreq"):
                        has_cpufreq = True
                    capacity = _read_int(
                        f"{self._cpu_dir}/{entry}/cpu_capacity", 0
                    ) or None
                    cpus.append(CPUCoreInfo(core=core_num, capacity=capacity))
        # os.listdir() order is arbitrary, so cpu7 could be reported before
        # cpu0. Sort numerically so the UI lists cores in a stable order.
        cpus.sort(key=lambda c: c.core)
        self._cpus = cpus
        self._has_cpufreq = has_cpufreq
        self._cpus_last_update = time.monotonic()


# ---------------------------------------------------------------------------
# RAM Collector
# ---------------------------------------------------------------------------

class RAMCollector(MetricCollector):
    """Collects RAM usage from /proc/meminfo.

    Uses a fixed 3s interval. The /proc/meminfo read is a single file
    read (no subprocess).
    """

    __slots__ = ("_interval_ms", "_buffer", "_stats", "_stop_event",
                 "_task")

    def __init__(self, interval_ms: int = SSE_RAM_INTERVAL_MS,
                 history_size: int = 20) -> None:
        super().__init__(interval_ms, history_size, "ram")

    async def collect(self) -> dict:
        """Return RAM metrics."""
        meminfo = self._parse_meminfo()
        if not meminfo:
            return {}

        total_kb = meminfo.get("MemTotal", 0)
        free_kb = meminfo.get("MemFree", 0)
        avail_kb = meminfo.get("MemAvailable", free_kb)
        used_kb = max(total_kb - avail_kb, 0)
        buffers_kb = meminfo.get("Buffers", 0)
        cached_kb = meminfo.get("Cached", 0)
        swap_total_kb = meminfo.get("SwapTotal", 0)
        swap_free_kb = meminfo.get("SwapFree", swap_total_kb)
        swap_used_kb = max(swap_total_kb - swap_free_kb, 0)

        used_pct = (used_kb / total_kb * 100.0) if total_kb > 0 else 0.0

        return {
            "total": total_kb,
            "free": free_kb,
            "available": avail_kb,
            "used": used_kb,
            "used_pct": used_pct,
            "buffers": buffers_kb,
            "cached": cached_kb,
            "swap_total": swap_total_kb,
            "swap_free": swap_free_kb,
            "swap_used": swap_used_kb,
        }

    def _parse_meminfo(self) -> Dict[str, int]:
        """Parse /proc/meminfo, return dict of kB values."""
        result: Dict[str, int] = {}
        text = _read_file("/proc/meminfo")
        if text is None:
            return result
        for line in text.splitlines():
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().split()[0]
            try:
                result[key] = int(val)
            except ValueError:
                pass
        return result


# ---------------------------------------------------------------------------
# Thermal Collector
# ---------------------------------------------------------------------------

@dataclass
class ThermalZone:
    name: str
    type: Optional[str] = None
    temp_millicelsius: Optional[int] = None
    temp_celsius: Optional[float] = None
    warning: bool = False
    crit: bool = False


# Thermal zone name mapping for readable labels
THERMAL_NAME_MAP = {
    "aoss_thermal": "AOSS (Always-On Sensor)",
    "aoss-thermal": "AOSS (Always-On Sensor)",
    "cpuss0_thermal": "CPU SS0 (Gold/Big)",
    "cpuss0-thermal": "CPU SS0 (Gold/Big)",
    "cpuss1_thermal": "CPU SS1 (LITTLE)",
    "cpuss1-thermal": "CPU SS1 (LITTLE)",
    "cpu0_thermal": "CPU0 (Gold)",
    "cpu0-thermal": "CPU0 (Gold)",
    "cpu1_thermal": "CPU1 (Gold)",
    "cpu1-thermal": "CPU1 (Gold)",
    "cpu2_thermal": "CPU2 (LITTLE)",
    "cpu2-thermal": "CPU2 (LITTLE)",
    "cpu3_thermal": "CPU3 (LITTLE)",
    "cpu3-thermal": "CPU3 (LITTLE)",
    "pwr_cluster_thermal": "Power Cluster",
    "pwr-cluster-thermal": "Power Cluster",
    "gpu_thermal": "GPU (Adreno)",
    "gpu-thermal": "GPU (Adreno)",
    "qcom_battery": "Battery",
    "qcom-battery": "Battery",
    "pm660_thermal": "PM660 (PMIC)",
    "pm660-thermal": "PM660 (PMIC)",
    "pm660l_thermal": "PM660L (PMIC)",
    "pm660l-thermal": "PM660L (PMIC)",
}


class ThermalCollector(MetricCollector):
    """Collects thermal zone data from hwmon and platform device sysfs.

    Tries multiple sysfs paths because thermal drivers differ by SoC.
    """

    __slots__ = ("_interval_ms", "_buffer", "_stats", "_stop_event",
                 "_task", "_sources")

    def __init__(self, interval_ms: int = SSE_THERMAL_INTERVAL_MS,
                 history_size: int = 20) -> None:
        super().__init__(interval_ms, history_size, "thermal")
        self._sources = self._discover_thermal_sources()

    async def collect(self) -> list:
        """Return list of ThermalZone dicts (JSON-serializable)."""
        zones: List[dict] = []
        seen_names: set = set()

        # 1) hwmon thermal zones
        hwmon_path = "/sys/class/hwmon"
        if os.path.isdir(hwmon_path):
            for hwmon_name in sorted(os.listdir(hwmon_path)):
                hwmon_dir = os.path.join(hwmon_path, hwmon_name)
                name_file = os.path.join(hwmon_dir, "name")
                dev_type = _read_file(name_file) or "unknown"
                for temp_i in range(10):  # hwmon typically has temp1..tempN
                    temp_file = os.path.join(hwmon_dir, f"temp{temp_i}_input")
                    temp_val = _read_int(temp_file, 0)
                    if temp_val <= 0:
                        continue  # no sensor here
                    label_file = os.path.join(hwmon_dir, f"temp{temp_i}_label")
                    label = _read_file(label_file) or f"hwmon-{hwmon_name}"
                    tc = temp_val / 1000.0
                    warning = tc >= 70.0
                    crit = tc >= 90.0
                    zone_name = f"{label}" if label else f"hwmon-{hwmon_name}-{temp_i}"
                    norm_type = dev_type.replace("-", "_")
                    if norm_type in seen_names:
                        continue  # already found via a previous source (e.g. platform)
                    seen_names.add(norm_type)
                    zones.append({
                        "name": zone_name,
                        "display_name": THERMAL_NAME_MAP.get(dev_type, zone_name),
                        "type": dev_type,
                        "temp_millicelsius": temp_val,
                        "temp_celsius": tc,
                        "warning": warning,
                        "crit": crit,
                    })

        # 2) platform device thermal (qcom, mediatek, etc.)
        platform_path = "/sys/bus/platform/devices"
        if os.path.isdir(platform_path):
            for dev_name in sorted(os.listdir(platform_path)):
                if "thermal" not in dev_name.lower() and "temp" not in dev_name.lower():
                    continue
                dev_dir = os.path.join(platform_path, dev_name)
                temp_file = os.path.join(dev_dir, "temp")
                temp_val = _read_int(temp_file, 0)
                if temp_val > 0:
                    tc = temp_val / 1000.0
                    warning = tc >= 70.0
                    crit = tc >= 90.0
                    zones.append({
                        "name": dev_name,
                        "display_name": THERMAL_NAME_MAP.get(dev_name, dev_name),
                        "type": "platform-thermal",
                        "temp_millicelsius": temp_val,
                        "temp_celsius": tc,
                        "warning": warning,
                        "crit": crit,
                    })

        # 3) legacy thermal sysfs (some kernels)
        thermal_path = "/sys/class/thermal"
        if os.path.isdir(thermal_path):
            for zone_name in sorted(os.listdir(thermal_path)):
                zone_dir = os.path.join(thermal_path, zone_name)
                type_file = os.path.join(zone_dir, "type")
                dev_type = _read_file(type_file) or "thermal"
                # Normalize: use underscores consistently for dedup key
                norm_type = dev_type.replace("-", "_")
                temp_file = os.path.join(zone_dir, "temp")
                temp_val = _read_int(temp_file, 0)
                if temp_val > 0:
                    # Skip duplicates already found via hwmon (same dev_type, normalized)
                    if norm_type in seen_names:
                        continue
                    seen_names.add(norm_type)
                    tc = temp_val / 1000.0
                    warning = tc >= 70.0
                    crit = tc >= 90.0
                    zones.append({
                        "name": zone_name,
                        "display_name": THERMAL_NAME_MAP.get(dev_type, zone_name),
                        "type": dev_type,
                        "temp_millicelsius": temp_val,
                        "temp_celsius": tc,
                        "warning": warning,
                        "crit": crit,
                    })

        return zones

    def _discover_thermal_sources(self) -> list:
        """Return list of thermal source paths for discovery (used by tests)."""
        return [
            "/sys/class/hwmon",
            "/sys/bus/platform/devices",
            "/sys/class/thermal",
        ]


# ---------------------------------------------------------------------------
# Battery Collector
# ---------------------------------------------------------------------------

@dataclass
class BatteryInfo:
    percentage: Optional[int] = None
    state: str = "unknown"
    temperature: Optional[float] = None
    voltage: Optional[float] = None
    energy_rate: Optional[float] = None
    time_to_full: Optional[int] = None  # seconds
    time_to_empty: Optional[int] = None
    energy: Optional[float] = None  # Wh
    energy_full: Optional[float] = None
    capacity: Optional[int] = None  # design capacity Wh
    discharging: bool = False
    charging: bool = False
    online: bool = False
    serial: Optional[str] = None
    vendor: str = ""
    model: str = ""
    icon_name: str = ""
    has_history: bool = False
    # Derived
    battery_state: str = "unknown"
    battery_level: str = ""
    battery_capacity_str: str = ""


class BatteryCollector(MetricCollector):
    """Collects battery info from sysfs power_supply and upower.

    Tries sysfs first (single file reads, no subprocess). Supplements with
    upower for fields like time_to_empty, time_to_full, and capacity.
    """

    __slots__ = ("_interval_ms", "_buffer", "_stats", "_stop_event",
                 "_task", "_sysfs_batteries", "_upower_available", "_upower_device")

    def __init__(self, interval_ms: int = SSE_BATTERY_INTERVAL_MS,
                 history_size: int = 20) -> None:
        super().__init__(interval_ms, history_size, "battery")
        self._sysfs_batteries: List[str] = []
        self._upower_available = False
        self._upower_device: Optional[str] = None

    async def collect(self) -> dict:
        """Return aggregated battery info (dict, not BatteryInfo dataclass,
        for JSON serialization in SSE)."""
        info = self._collect_sysfs()
        upower_info = await asyncio.to_thread(self._collect_upower)
        if upower_info:
            for k, v in upower_info.items():
                if v is not None:
                    if info.get(k) is None or info.get(k) == "" or info.get(k) == "unknown":
                        info[k] = v
                    elif k in ("time_to_empty", "time_to_full", "capacity"):
                        info[k] = v
                    elif k == "energy_rate" and (not info.get("energy_rate") or info.get("energy_rate") <= 0):
                        info[k] = v

        state = str(info.get("state") or "unknown").lower()
        info["charging"] = state == "charging"
        info["discharging"] = state == "discharging"
        if info.get("percentage") is not None:
            info["battery_level"] = f"{info['percentage']}%"
        info["battery_state"] = state
        if info.get("capacity") is not None:
            info["battery_capacity_str"] = f"{info['capacity']}%"
        return info

    def _collect_sysfs(self) -> dict:
        """Read all battery-related sysfs entries in one pass."""
        batteries = self._discover_batteries()
        result: dict = {
            "percentage": None,
            "state": "unknown",
            "temperature": None,
            "voltage": None,
            "energy_rate": None,
            "time_to_full": None,
            "time_to_empty": None,
            "energy": None,
            "energy_full": None,
            "capacity": None,
            "charging": False,
            "discharging": False,
            "online": False,
            "serial": None,
            "vendor": "",
            "model": "",
            "icon_name": "",
            "has_history": False,
            "battery_state": "unknown",
            "battery_level": "",
            "battery_capacity_str": "",
        }

        if not batteries:
            return result

        # Aggregate from sysfs
        total_pct = 0
        pct_count = 0
        charge_state = "unknown"
        temp = None
        volt = None
        energy_rate = None
        online = False
        serial = None
        vendor = ""
        model = ""
        icon_name = ""
        has_history = False
        energy = None
        energy_full = None
        capacity = None
        capacity_num = 0
        capacity_den = 0

        for batt in batteries:
            cap_file = f"/sys/class/power_supply/{batt}/capacity"
            cap = _read_int(cap_file)
            if cap >= 0:
                total_pct += cap
                pct_count += 1

            status_file = f"/sys/class/power_supply/{batt}/status"
            status = _read_file(status_file)
            if status:
                st = status.lower()
                if st == "charging":
                    charge_state = "charging"
                elif st == "discharging":
                    charge_state = "discharging"
                elif st in ("full", "fully-charged"):
                    charge_state = "full"
                elif st in ("not charging", "idle"):
                    charge_state = "not charging"

            online_file = f"/sys/class/power_supply/{batt}/online"
            online_val = _read_int(online_file, 0)
            if online_val:
                online = True

            temp_file = f"/sys/class/power_supply/{batt}/temp"
            tv = _read_int(temp_file, 0)
            if tv > 0:
                if tv > 1000:
                    temp_c = tv / 1000.0
                else:
                    temp_c = tv / 10.0
                if temp is None or temp_c > temp:
                    temp = temp_c

            volt_file = f"/sys/class/power_supply/{batt}/voltage_now"
            v = _read_int(volt_file, 0)
            if v > 0:
                voltage_val = v / 1_000_000.0
                if volt is None or voltage_val > volt:
                    volt = voltage_val

            energy_rate_file = f"/sys/class/power_supply/{batt}/power_now"
            er = _read_int(energy_rate_file, 0)
            if er > 0:
                rate_val = er / 1_000_000.0  # uW -> W
                if energy_rate is None or rate_val > energy_rate:
                    energy_rate = rate_val
            elif v > 0:
                curr_file = f"/sys/class/power_supply/{batt}/current_now"
                cr = _read_int(curr_file, 0)
                if cr != 0:
                    rate_val = abs(cr * v) / 1_000_000_000_000.0
                    if energy_rate is None or rate_val > energy_rate:
                        energy_rate = rate_val

            serial_file = f"/sys/class/power_supply/{batt}/serial_number"
            s = _read_file(serial_file)
            if s:
                serial = s

            vendor_file = f"/sys/class/power_supply/{batt}/manufacturer"
            v2 = _read_file(vendor_file)
            if v2:
                vendor = v2

            model_file = f"/sys/class/power_supply/{batt}/model_name"
            m = _read_file(model_file)
            if m:
                model = m

            icon_file = f"/sys/class/power_supply/{batt}/uevent"
            iev = _read_file(icon_file)
            if iev:
                for line2 in iev.splitlines():
                    if line2.startswith("POWER_SUPPLY_ICON="):
                        icon_name = line2.split("=", 1)[1].strip()

            efd_file = f"/sys/class/power_supply/{batt}/energy_full_design"
            efd = _read_int(efd_file, 0)
            if efd > 0:
                has_history = True

            ef_file = f"/sys/class/power_supply/{batt}/energy_full"
            ef = _read_int(ef_file, 0)
            if ef > 0:
                energy_full = ef / 1_000_000.0
            elif v > 0:
                cf_file = f"/sys/class/power_supply/{batt}/charge_full"
                cf = _read_int(cf_file, 0)
                if cf > 0:
                    energy_full = (cf * v) / 1_000_000_000_000.0

            if efd > 0 and ef > 0:
                capacity_num += ef
                capacity_den += efd
            else:
                cfd_file = f"/sys/class/power_supply/{batt}/charge_full_design"
                cfd = _read_int(cfd_file, 0)
                cf_file = f"/sys/class/power_supply/{batt}/charge_full"
                cf = _read_int(cf_file, 0)
                if cfd > 0 and cf > 0:
                    capacity_num += cf
                    capacity_den += cfd

            e_file = f"/sys/class/power_supply/{batt}/energy_now"
            e = _read_int(e_file, 0)
            if e > 0:
                energy = e / 1_000_000.0
            elif v > 0:
                cn_file = f"/sys/class/power_supply/{batt}/charge_now"
                cn = _read_int(cn_file, 0)
                if cn > 0:
                    energy = (cn * v) / 1_000_000_000_000.0

        if pct_count > 0:
            result["percentage"] = total_pct // pct_count
        result["state"] = charge_state
        result["temperature"] = temp
        result["voltage"] = volt
        result["energy_rate"] = energy_rate
        result["online"] = online
        result["serial"] = serial
        result["vendor"] = vendor
        result["model"] = model
        result["icon_name"] = icon_name
        result["has_history"] = has_history
        result["energy"] = energy
        result["energy_full"] = energy_full
        if capacity_den > 0:
            capacity = round((capacity_num / capacity_den) * 100, 1)
        result["capacity"] = capacity

        # Derive human-readable fields
        pct = result["percentage"]
        if pct is not None:
            result["battery_level"] = f"{pct}%"
        result["battery_state"] = charge_state
        if result["capacity"] is not None:
            result["battery_capacity_str"] = f"{result['capacity']}%"
        elif result["has_history"]:
            result["battery_capacity_str"] = "unknown"
        else:
            result["battery_capacity_str"] = "N/A"

        result["charging"] = charge_state in ("charging", "full")
        result["discharging"] = charge_state == "discharging"

        return result

    def _discover_batteries(self) -> List[str]:
        """Find battery devices in /sys/class/power_supply."""
        batteries = []
        ps_path = "/sys/class/power_supply"
        if not os.path.isdir(ps_path):
            return batteries
        for name in os.listdir(ps_path):
            if (name.startswith("bat") or "battery" in name.lower()
                    or name.startswith("qcom-battery")):
                batteries.append(name)
        return batteries

    def _get_upower_device(self) -> Optional[str]:
        """Dynamically detect battery device path in upower."""
        if self._upower_device:
            return self._upower_device
        import subprocess
        try:
            out = subprocess.check_output(["upower", "-e"], timeout=3).decode("utf-8")
            for line in out.splitlines():
                line = line.strip()
                if "battery" in line.lower() and "line_power" not in line.lower():
                    self._upower_device = line
                    return self._upower_device
        except Exception:
            pass
        return None

    def _collect_upower(self) -> dict:
        """Fallback and supplement via upower."""
        if not self._upower_available:
            import subprocess
            try:
                subprocess.run(["upower", "--version"], capture_output=True, timeout=2)
                self._upower_available = True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                self._upower_available = False

        if not self._upower_available:
            return {}

        dev = self._get_upower_device()
        if not dev:
            return {}

        import subprocess
        try:
            out = subprocess.check_output(
                ["upower", "-i", dev],
                timeout=4, stderr=subprocess.STDOUT,
            ).decode("utf-8", errors="replace")
        except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return {}

        result: dict = {}
        for line in out.splitlines():
            line = line.strip()
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            key = key.strip().lower().replace("-", " ").replace("_", " ")
            val = val.strip()
            if key == "percentage":
                try:
                    result["percentage"] = int(float(val.replace("%", "").strip()))
                except ValueError:
                    pass
            elif key == "state":
                result["state"] = val
            elif key == "temperature":
                try:
                    result["temperature"] = float(val.replace("degrees C", "").replace("°C", "").strip())
                except ValueError:
                    pass
            elif key == "voltage":
                try:
                    result["voltage"] = float(val.replace("V", "").strip())
                except ValueError:
                    pass
            elif key in ("energy rate", "energy_rate"):
                try:
                    result["energy_rate"] = float(val.replace("W", "").strip())
                except ValueError:
                    pass
            elif key in ("time to full", "time_to_full"):
                result["time_to_full"] = val
            elif key in ("time to empty", "time_to_empty"):
                result["time_to_empty"] = val
            elif key == "energy":
                try:
                    result["energy"] = float(val.replace("Wh", "").strip())
                except ValueError:
                    pass
            elif key in ("energy full", "energy_full"):
                try:
                    result["energy_full"] = float(val.replace("Wh", "").strip())
                except ValueError:
                    pass
            elif key == "capacity":
                try:
                    result["capacity"] = round(float(val.replace("%", "").strip()), 1)
                except ValueError:
                    pass
            elif key == "serial":
                result["serial"] = val
            elif key == "vendor":
                result["vendor"] = val
            elif key == "model":
                result["model"] = val
            elif key in ("icon name", "icon_name"):
                result["icon_name"] = val
            elif key == "has history":
                result["has_history"] = val.lower() == "yes"

        return result


# ---------------------------------------------------------------------------
# Network Rate Collector
# ---------------------------------------------------------------------------

class NetworkRateCollector(MetricCollector):
    """Collects network interface counters from /proc/net/dev and computes
    rates (bytes/sec) by comparing consecutive samples.

    Uses a rolling delta: each sample stores current counters, next sample
    computes (new - old) / elapsed.
    """

    __slots__ = ("_interval_ms", "_buffer", "_stats", "_stop_event",
                 "_task", "_prev_counters", "_prev_time")

    def __init__(self, interval_ms: int = SSE_NETWORK_INTERVAL_MS,
                 history_size: int = 30) -> None:
        super().__init__(interval_ms, history_size, "network")
        self._prev_counters: Dict[str, Tuple[int, int]] = {}
        self._prev_time: float = 0.0

    async def collect(self) -> dict:
        """Return network rate for the primary non-loopback interface."""
        now = time.monotonic()
        counters = self._read_network_counters()

        iface = self._primary_interface(counters)
        if iface is None or iface not in counters:
            return {
                "iface": iface or "none",
                "rx_rate_bps": 0,
                "tx_rate_bps": 0,
            }

        rx_bytes, tx_bytes = counters[iface]
        rx_rate = 0.0
        tx_rate = 0.0

        if self._prev_time > 0 and iface in self._prev_counters:
            prev_rx, prev_tx = self._prev_counters[iface]
            elapsed = now - self._prev_time
            if elapsed > 0:
                rx_rate = (rx_bytes - prev_rx) / elapsed
                tx_rate = (tx_bytes - prev_tx) / elapsed

        self._prev_counters[iface] = (rx_bytes, tx_bytes)
        self._prev_time = now

        return {
            "iface": iface,
            "rx_bytes": rx_bytes,
            "tx_bytes": tx_bytes,
            "rx_rate_bps": rx_rate,
            "tx_rate_bps": tx_rate,
        }

    def _read_network_counters(self) -> Dict[str, Tuple[int, int]]:
        """Read /proc/net/dev, return {iface: (rx_bytes, tx_bytes)}."""
        counters: Dict[str, Tuple[int, int]] = {}
        text = _read_file("/proc/net/dev")
        if text is None:
            return counters
        lines = text.splitlines()
        # Skip header lines
        for line in lines[2:]:
            parts = line.split()
            if len(parts) < 10:
                continue
            iface = parts[0].rstrip(":")
            rx_bytes = int(parts[1])
            tx_bytes = int(parts[9])
            counters[iface] = (rx_bytes, tx_bytes)
        return counters

    def _primary_interface(self, counters: Dict[str, Tuple[int, int]]) -> Optional[str]:
        """Pick the best interface to report: prefer non-loopback, non-veth,
        exclude lo, docker, bridge, tun, tap. Prefer interfaces with actual
        traffic (non-zero rx_bytes) over idle interfaces like usb0."""
        exclude = {"lo", "docker", "br-", "veth", "tun", "tap", "virbr", "bond"}
        candidates = []
        for iface in sorted(counters.keys()):
            if any(iface.startswith(p) for p in exclude):
                continue
            candidates.append(iface)
        if not candidates:
            # Fallback to any non-loopback interface
            for iface in sorted(counters.keys()):
                if iface != "lo":
                    return iface
            return None
        # Prefer interfaces with actual traffic (non-zero rx_bytes)
        for iface in candidates:
            rx_bytes, _ = counters[iface]
            if rx_bytes > 0:
                return iface
        # All candidates have zero traffic — return the first one
        return candidates[0]


# ---------------------------------------------------------------------------
# Live Monitoring Engine (singleton orchestrator)
# ---------------------------------------------------------------------------

class LiveMonitor:
    """Orchestrates all per-metric collectors.

    - Lazy start: collectors start when first client connects
    - Stop when last client disconnects
    - Expose current values + buffers for SSE streaming
    """

    __slots__ = ("_cpu", "_ram", "_thermal", "_battery", "_network",
                 "_lock", "_client_count", "_started")

    def __init__(self) -> None:
        self._cpu = CPUFreqCollector()
        self._ram = RAMCollector()
        self._thermal = ThermalCollector()
        self._battery = BatteryCollector()
        self._network = NetworkRateCollector()
        self._lock = asyncio.Lock()
        self._client_count = 0
        self._started = False

    @property
    def cpu(self) -> CPUFreqCollector:
        return self._cpu

    @property
    def ram(self) -> RAMCollector:
        return self._ram

    @property
    def thermal(self) -> ThermalCollector:
        return self._thermal

    @property
    def battery(self) -> BatteryCollector:
        return self._battery

    @property
    def network(self) -> NetworkRateCollector:
        return self._network

    async def _ensure_started(self) -> None:
        """Start all collectors. Caller must hold ``_lock``."""
        if self._started:
            return
        loop = asyncio.get_running_loop()
        self._cpu.start(loop)
        self._ram.start(loop)
        self._thermal.start(loop)
        self._battery.start(loop)
        self._network.start(loop)
        self._started = True

    async def _ensure_stopped(self) -> None:
        """Stop all collectors. Caller must hold ``_lock``."""
        if not self._started:
            return
        self._cpu.stop()
        self._ram.stop()
        self._thermal.stop()
        self._battery.stop()
        self._network.stop()
        self._started = False

    async def add_client(self) -> None:
        # The refcount bump and the start decision must be atomic together,
        # otherwise a client arriving while the last one is still tearing down
        # sees _started=True, skips the start, and then the departing client
        # flips _started=False — leaving a live subscriber with dead collectors.
        async with self._lock:
            self._client_count += 1
            if self._client_count == 1:
                await self._ensure_started()

    async def remove_client(self) -> None:
        async with self._lock:
            if self._client_count > 0:
                self._client_count -= 1
            if self._client_count == 0:
                await self._ensure_stopped()

    async def get_cpu(self) -> dict:
        return await self._cpu.collect()

    async def get_ram(self) -> dict:
        return await self._ram.collect()

    async def get_thermal(self) -> list:
        return await self._thermal.collect()

    async def get_battery(self) -> dict:
        return await self._battery.collect()

    async def get_network(self) -> dict:
        return await self._network.collect()

    async def get_all_metrics(self) -> dict:
        return {
            "cpu": await self.get_cpu(),
            "ram": await self.get_ram(),
            "thermal": await self.get_thermal(),
            "battery": await self.get_battery(),
            "network": await self.get_network(),
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_live_monitor: Optional[LiveMonitor] = None

def get_live_monitor() -> LiveMonitor:
    global _live_monitor
    if _live_monitor is None:
        _live_monitor = LiveMonitor()
    return _live_monitor