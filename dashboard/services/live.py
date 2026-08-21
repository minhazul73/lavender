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
# CPU Frequency Collector
# ---------------------------------------------------------------------------

@dataclass
class CPUCoreInfo:
    core: int
    frequency_mhz: Optional[float] = None   # None if cpufreq not exposed
    governor: Optional[str] = None


class CPUFreqCollector(MetricCollector):
    """Collects per-core CPU frequency from sysfs.

    Falls back to count-only if cpufreq sysfs is unavailable (e.g. some
    ARM SoCs without dynamic frequency scaling).
    """

    __slots__ = ("_cpu_dir", "_cpus", "_cpus_last_update", "_interval_ms",
                 "_buffer", "_stats", "_stop_event", "_task")

    def __init__(self, interval_ms: int = SSE_CPU_INTERVAL_MS,
                 history_size: int = 20) -> None:
        super().__init__(interval_ms, history_size, "cpu")
        self._cpu_dir = "/sys/devices/system/cpu"
        self._cpus: List[CPUCoreInfo] = []
        self._cpus_last_update = 0.0

    async def collect(self) -> dict:
        """Return CPU info: count, per-core list (as plain dicts for JSON),
        first-core freq for sparkline."""
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
            })

        freqs = [c["frequency_mhz"] for c in cores_list if c["frequency_mhz"] is not None]
        primary_freq = freqs[0] if freqs else None

        return {
            "cpus": cores_list,
            "count": len(cores),
            "primary_frequency_mhz": primary_freq,
        }

    def _discover_cpus(self) -> None:
        cpus = []
        if not os.path.isdir(self._cpu_dir):
            return
        for entry in os.listdir(self._cpu_dir):
            if entry.startswith("cpu") and entry[3:].isdigit():
                core_num = int(entry[3:])
                online_path = f"{self._cpu_dir}/{entry}/online"
                online = _read_int(online_path, 1)
                if online:
                    cpus.append(CPUCoreInfo(core=core_num))
        self._cpus = cpus
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

        total_mb = total_kb / 1024.0
        used_pct = (used_kb / total_kb * 100.0) if total_kb > 0 else 0.0

        return {
            "total": total_mb,
            "free": free_kb / 1024.0,
            "available": avail_kb / 1024.0,
            "used": used_kb / 1024.0,
            "used_pct": used_pct,
            "buffers": buffers_kb / 1024.0,
            "cached": cached_kb / 1024.0,
            "swap_total": swap_total_kb / 1024.0,
            "swap_free": swap_free_kb / 1024.0,
            "swap_used": swap_used_kb / 1024.0,
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
                    if zone_name not in seen_names:
                        seen_names.add(zone_name)
                    else:
                        zone_name = f"{zone_name}-{temp_i}"
                    zones.append({
                        "name": zone_name,
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
                temp_file = os.path.join(zone_dir, "temp")
                temp_val = _read_int(temp_file, 0)
                if temp_val > 0:
                    tc = temp_val / 1000.0
                    warning = tc >= 70.0
                    crit = tc >= 90.0
                    zones.append({
                        "name": zone_name,
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

    Tries sysfs first (single file reads, no subprocess). Falls back to
    upower only if needed for additional fields like time_to_full.
    """

    __slots__ = ("_interval_ms", "_buffer", "_stats", "_stop_event",
                 "_task", "_sysfs_batteries", "_upower_available")

    def __init__(self, interval_ms: int = SSE_BATTERY_INTERVAL_MS,
                 history_size: int = 20) -> None:
        super().__init__(interval_ms, history_size, "battery")
        self._sysfs_batteries: List[str] = []
        self._upower_available = False

    async def collect(self) -> dict:
        """Return aggregated battery info (dict, not BatteryInfo dataclass,
        for JSON serialization in SSE)."""
        info = self._collect_sysfs()
        if info.get("online"):
            # Supplement with upower for time_to_full/empty if available
            upower_info = self._collect_upower()
            info.update(upower_info)
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
            # No battery sysfs — try to get whatever we can from upower
            up = self._collect_upower()
            if up.get("percentage") is not None:
                result["percentage"] = up["percentage"]
                result["state"] = up.get("state", "unknown")
                result["temperature"] = up.get("temperature")
                result["voltage"] = up.get("voltage")
                result["energy_rate"] = up.get("energy_rate")
                result["time_to_full"] = up.get("time_to_full")
                result["time_to_empty"] = up.get("time_to_empty")
                result["energy"] = up.get("energy")
                result["energy_full"] = up.get("energy_full")
                result["capacity"] = up.get("capacity")
                result["charging"] = up.get("charging", False)
                result["discharging"] = up.get("discharging", False)
                result["online"] = up.get("online", False)
                result["serial"] = up.get("serial")
                result["vendor"] = up.get("vendor", "")
                result["model"] = up.get("model", "")
                result["icon_name"] = up.get("icon_name", "")
                result["has_history"] = up.get("has_history", False)
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

        for batt in batteries:
            cap_file = f"/sys/class/power_supply/{batt}/capacity"
            cap = _read_int(cap_file)
            if cap >= 0:
                total_pct += cap
                pct_count += 1

            status_file = f"/sys/class/power_supply/{batt}/status"
            status = _read_file(status_file)
            if status:
                if status.lower() == "charging":
                    charge_state = "charging"
                elif status.lower() == "discharging":
                    charge_state = "discharging"
                elif status.lower() == "full":
                    charge_state = "full"
                elif status.lower() == "not charging":
                    charge_state = "charging"  # plugged but not actively charging
                elif status.lower() == "unknown":
                    pass

            online_file = f"/sys/class/power_supply/{batt}/online"
            online_val = _read_int(online_file, 0)
            if online_val:
                online = True

            temp_file = f"/sys/class/power_supply/{batt}/temp"
            tv = _read_int(temp_file, 0)
            if tv > 0:
                # qcom-battery reports temp in decidegrees (395 = 39.5°C)
                # hwmon reports in millidegrees (49300 = 49.3°C)
                # Detect which: values > 1000 are likely millidegrees
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

            # History (energy_full_design vs energy_full)
            efd_file = f"/sys/class/power_supply/{batt}/energy_full_design"
            efd = _read_int(efd_file, 0)
            if efd > 0:
                capacity = efd / 1_000_000.0  # uWh -> Wh
                has_history = True

            ef_file = f"/sys/class/power_supply/{batt}/energy_full"
            ef = _read_int(ef_file, 0)
            if ef > 0:
                energy_full = ef / 1_000_000.0

            e_file = f"/sys/class/power_supply/{batt}/energy_now"
            e = _read_int(e_file, 0)
            if e > 0:
                energy = e / 1_000_000.0

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
        result["capacity"] = capacity

        # Derive human-readable fields
        pct = result["percentage"]
        if pct is not None:
            result["battery_level"] = f"{pct}%"
        result["battery_state"] = charge_state
        if result["capacity"] is not None:
            result["battery_capacity_str"] = f"{result['capacity']} Wh"
        elif result["has_history"]:
            result["battery_capacity_str"] = "unknown"
        else:
            result["battery_capacity_str"] = "N/A"

        result["charging"] = charge_state in ("charging", "full")
        result["discharging"] = charge_state == "discharging"

        # Try upower for time_to_full/empty (not available in sysfs on all devices)
        if result["online"]:
            up = self._collect_upower()
            if up.get("time_to_full") is not None:
                result["time_to_full"] = up["time_to_full"]
            if up.get("time_to_empty") is not None:
                result["time_to_empty"] = up["time_to_empty"]

        return result

    def _discover_batteries(self) -> List[str]:
        """Find battery devices in /sys/class/power_supply."""
        batteries = []
        ps_path = "/sys/class/power_supply"
        if not os.path.isdir(ps_path):
            return batteries
        for name in os.listdir(ps_path):
            # Match bat*, qcom-battery, and any device with battery in name
            if (name.startswith("bat") or "battery" in name.lower()
                    or name.startswith("qcom-battery")):
                batteries.append(name)
        return batteries

    def _collect_upower(self) -> dict:
        """Fallback to upower for fields not in sysfs.

        Lazily checks if upower is available (subprocess once, cached).
        """
        if not self._upower_available:
            import subprocess
            try:
                subprocess.run(["upower", "--version"], capture_output=True, timeout=2)
                self._upower_available = True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                self._upower_available = False

        if not self._upower_available:
            return {}

        import subprocess
        try:
            out = subprocess.check_output(
                ["upower", "-i", "/org/freedesktop/UPower/devices/battery_BAT0"],
                timeout=5, stderr=subprocess.STDOUT,
            ).decode("utf-8", errors="replace")
        except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return {}

        result: dict = {}
        for line in out.splitlines():
            line = line.strip()
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            key = key.strip().lower().replace(" ", "_")
            val = val.strip()
            if key == "percentage":
                try:
                    result["percentage"] = int(val.replace("%", "").strip())
                except ValueError:
                    pass
            elif key == "state":
                result["state"] = val
            elif key == "temperature":
                try:
                    result["temperature"] = float(val)
                except ValueError:
                    pass
            elif key == "voltage":
                try:
                    result["voltage"] = float(val.replace("V", "").strip())
                except ValueError:
                    pass
            elif key == "energy_rate":
                try:
                    result["energy_rate"] = float(val.replace("W", "").strip())
                except ValueError:
                    pass
            elif key == "time to full":
                try:
                    ttf = val.replace("minutes", "").strip()
                    result["time_to_full"] = int(ttf)
                except ValueError:
                    pass
            elif key == "time to empty":
                try:
                    tte = val.replace("minutes", "").strip()
                    result["time_to_empty"] = int(tte)
                except ValueError:
                    pass
            elif key == "energy":
                try:
                    result["energy"] = float(val.replace("Wh", "").strip())
                except ValueError:
                    pass
            elif key == "energy full":
                try:
                    result["energy_full"] = float(val.replace("Wh", "").strip())
                except ValueError:
                    pass
            elif key == "capacity":
                try:
                    result["capacity"] = int(val.replace("Wh", "").strip())
                except ValueError:
                    pass
            elif key == "charging":
                result["charging"] = val.lower() == "yes"
            elif key == "discharging":
                result["discharging"] = val.lower() == "yes"
            elif key == "online":
                result["online"] = val.lower() == "yes"
            elif key == "serial":
                result["serial"] = val
            elif key == "vendor":
                result["vendor"] = val
            elif key == "model":
                result["model"] = val
            elif key == "icon_name":
                result["icon_name"] = val
            elif key == "has_history":
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
        exclude lo, docker, bridge, tun, tap."""
        exclude = {"lo", "docker", "br-", "veth", "tun", "tap", "virbr", "bond"}
        candidates = []
        for iface in sorted(counters.keys()):
            if any(iface.startswith(p) for p in exclude):
                continue
            candidates.append(iface)
        if candidates:
            return candidates[0]
        # Fallback to any interface
        for iface in sorted(counters.keys()):
            if iface != "lo":
                return iface
        return None


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
        if self._started:
            return
        async with self._lock:
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
        if not self._started:
            return
        async with self._lock:
            if not self._started:
                return
            self._cpu.stop()
            self._ram.stop()
            self._thermal.stop()
            self._battery.stop()
            self._network.stop()
            self._started = False

    async def add_client(self) -> None:
        self._client_count += 1
        if self._client_count == 1:
            await self._ensure_started()

    async def remove_client(self) -> None:
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