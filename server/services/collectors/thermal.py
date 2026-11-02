"""
Thermal zone data collector from hwmon and platform device sysfs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

from server.core.config import SSE_THERMAL_INTERVAL_MS
from server.services.live_buffer import MetricCollector


def _read_file(path: str) -> Optional[str]:
    import server.services.live as live
    return live._read_file(path)


def _read_int(path: str, default: int = 0) -> int:
    import server.services.live as live
    return live._read_int(path, default)


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
