"""
CPU frequency and per-core usage collector.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import List, Optional

from server.core.config import SSE_CPU_INTERVAL_MS
from server.services.live_buffer import MetricCollector


def _read_file(path: str) -> Optional[str]:
    import server.services.live as live
    return live._read_file(path)


def _read_int(path: str, default: int = 0) -> int:
    import server.services.live as live
    return live._read_int(path, default)


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


CpuCollector = CPUFreqCollector
