"""
Battery info collector from sysfs power_supply and upower.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import List, Optional

from server.core.config import SSE_BATTERY_INTERVAL_MS
from server.services.live_buffer import MetricCollector


def _read_file(path: str) -> Optional[str]:
    import server.services.live as live
    return live._read_file(path)


def _read_int(path: str, default: int = 0) -> int:
    import server.services.live as live
    return live._read_int(path, default)


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
                 "_task", "_sysfs_batteries", "_upower_available",
                 "_upower_checked", "_upower_device")

    def __init__(self, interval_ms: int = SSE_BATTERY_INTERVAL_MS,
                 history_size: int = 20) -> None:
        super().__init__(interval_ms, history_size, "battery")
        self._sysfs_batteries: List[str] = []
        self._upower_available = False
        self._upower_checked = False
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
        if self._upower_device is not None:
            return self._upower_device or None
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
        self._upower_device = ""
        return None

    def _collect_upower(self) -> dict:
        """Fallback and supplement via upower."""
        if not self._upower_checked:
            import subprocess
            try:
                subprocess.run(["upower", "--version"], capture_output=True, timeout=2)
                self._upower_available = True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                self._upower_available = False
            self._upower_checked = True

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
