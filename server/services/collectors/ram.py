"""
RAM metric collector from /proc/meminfo.
"""

from __future__ import annotations

from typing import Dict, Optional

from server.core.config import SSE_RAM_INTERVAL_MS
from server.services.live_buffer import MetricCollector


def _read_file(path: str) -> Optional[str]:
    import server.services.live as live
    return live._read_file(path)


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


RamCollector = RAMCollector
