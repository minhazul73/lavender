"""
Live telemetry orchestrator and backward-compatible collector facade.
"""

from __future__ import annotations

from server.core.sysfs import get_sysfs_reader

# Backward-compat re-exports — importers can use canonical paths directly
from server.services.collectors.battery import BatteryCollector, BatteryInfo  # noqa: F401
from server.services.collectors.network import NetworkCollector, NetworkRateCollector  # noqa: F401
from server.services.collectors.ram import RAMCollector, RamCollector  # noqa: F401

# Import the split-out LiveMonitor implementation
from server.services.live_monitor import LiveMonitor, get_live_monitor  # noqa: F401


# Shared sysfs helpers (kept here for backward compatibility and test patching)
# ---------------------------------------------------------------------------
def _read_file(path: str) -> str | None:
    """Read a single sysfs/proc file via swappable sysfs reader."""
    return get_sysfs_reader().read_file(path)

def _read_int(path: str, default: int = 0) -> int:
    """Read an integer from a sysfs/proc file."""
    return get_sysfs_reader().read_int(path, default)

def _read_float(path: str, default: float = 0.0) -> float:
    """Read a float from a sysfs/proc file."""
    return get_sysfs_reader().read_float(path, default)
