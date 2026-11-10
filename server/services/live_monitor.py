"""Live telemetry orchestrator and backward-compatible facade."""

from __future__ import annotations

import asyncio

from server.services.collectors.battery import BatteryCollector
from server.services.collectors.cpu import CPUFreqCollector
from server.services.collectors.network import NetworkRateCollector
from server.services.collectors.ram import RAMCollector
from server.services.collectors.thermal import ThermalCollector


class LiveCapacityError(Exception):
    """Raised when concurrent live subscribers exceed maximum allowed capacity."""


MAX_LIVE_CLIENTS = 50


class LiveMonitor:
    """Orchestrates all per-metric collectors.

    - Lazy start: collectors start when first client connects
    - Stop when last client disconnects
    - Expose current values + buffers for SSE streaming
    """
    __slots__ = (
        "_cpu", "_ram", "_thermal", "_battery", "_network",
        "_lock", "_client_count", "_started"
    )

    def __init__(self) -> None:
        """Initialize LiveMonitor with metric collectors and subscriber tracking."""
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
        """Collector for CPU frequency metrics."""
        return self._cpu

    @property
    def ram(self) -> RAMCollector:
        """Collector for memory usage metrics."""
        return self._ram

    @property
    def thermal(self) -> ThermalCollector:
        """Collector for thermal sensor metrics."""
        return self._thermal

    @property
    def battery(self) -> BatteryCollector:
        """Collector for power supply and battery metrics."""
        return self._battery

    @property
    def network(self) -> NetworkRateCollector:
        """Collector for network transfer rate metrics."""
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
        """Register active subscriber, starting collectors if first client."""
        async with self._lock:
            if self._client_count >= MAX_LIVE_CLIENTS:
                raise LiveCapacityError("Maximum live SSE clients reached")
            self._client_count += 1
            if self._client_count == 1:
                await self._ensure_started()

    async def remove_client(self) -> None:
        """Deregister subscriber, stopping collectors if none remain."""
        async with self._lock:
            if self._client_count > 0:
                self._client_count -= 1
            if self._client_count == 0:
                await self._ensure_stopped()

    async def get_cpu(self) -> dict:
        """Collect current CPU frequency data."""
        return await self._cpu.collect()

    async def get_ram(self) -> dict:
        """Collect current RAM utilization data."""
        return await self._ram.collect()

    async def get_thermal(self) -> list:
        """Collect current thermal zones temperature data."""
        return await self._thermal.collect()

    async def get_battery(self) -> dict:
        """Collect current battery and power supply data."""
        return await self._battery.collect()

    async def get_network(self) -> dict:
        """Collect current network interface rate data."""
        return await self._network.collect()

    async def get_all_metrics(self) -> dict:
        """Aggregate and return latest readings from all collectors."""
        return {
            "cpu": await self.get_cpu(),
            "ram": await self.get_ram(),
            "thermal": await self.get_thermal(),
            "battery": await self.get_battery(),
            "network": await self.get_network(),
        }


_live_monitor: LiveMonitor | None = None


def get_live_monitor() -> LiveMonitor:
    """Return the singleton LiveMonitor instance."""
    global _live_monitor
    if _live_monitor is None:
        _live_monitor = LiveMonitor()
    return _live_monitor
