"""
Battery, thermal, and CPU frequency management.
"""
import os
import re
import subprocess
import time

from server.core.executor import get_executor
from server.utils.async_safety import assert_not_in_running_loop
from server.utils.thermal import THERMAL_NAME_MAP

_BATTERY_CACHE_TTL: float = 5.0
_battery_cache: tuple[float, dict] | None = None


def _clear_battery_cache() -> None:
    """Clear internal battery cache (useful for testing)."""
    global _battery_cache
    _battery_cache = None


def run_command(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    res = get_executor().run_sync(cmd, timeout=float(timeout))
    return res.returncode, res.stdout, res.stderr


def run_sudo_command(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    full_cmd = ["sudo"] + cmd if cmd and cmd[0] == "-n" else ["sudo", "-n"] + cmd
    return run_command(full_cmd, timeout)


def _get_upower_device() -> str | None:
    """Dynamically detect battery device path in upower.

    Returns:
        The battery device path string, or None if discovery fails.
    """
    code, out, _ = run_command(["upower", "-e"], timeout=10)
    if code == 0:
        for line in out.splitlines():
            line = line.strip()
            if "battery" in line.lower() and "line_power" not in line.lower():
                if line:
                    return line
    return None


def _safe_float(val: str, suffix: str = "") -> float | None:
    try:
        return float(val.replace(suffix, "").strip())
    except (ValueError, AttributeError):
        return None


def _safe_int(val: str, suffix: str = "") -> int | None:
    try:
        return int(val.replace(suffix, "").strip())
    except (ValueError, AttributeError):
        return None


def _parse_upower_kv(out: str) -> dict[str, str]:
    info: dict[str, str] = {}
    current_key = None
    for raw_line in out.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip()
            if val:
                info[key] = val
                current_key = None
            else:
                current_key = key
                info[current_key] = ""
        elif current_key:
            info[current_key] = f"{info[current_key]} {line}".strip()
    return info


def _parse_numeric_fields(k: str, val: str, result: dict) -> None:
    if "percentage" in k:
        result["percentage"] = _safe_int(val, "%")
    elif k == "voltage":
        result["voltage"] = _safe_float(val, "V")
    elif "voltage-min-design" in k:
        result["voltage_min_design"] = _safe_float(val, "V")
    elif "voltage-max-design" in k:
        result["voltage_max_design"] = _safe_float(val, "V")
    elif k == "energy":
        result["energy"] = _safe_float(val, "Wh")
    elif "energy-full-design" in k:
        result["energy_full_design"] = _safe_float(val, "Wh")
    elif "energy-full" in k:
        result["energy_full"] = _safe_float(val, "Wh")
    elif "energy-rate" in k:
        result["energy_rate"] = _safe_float(val, "W")
    elif "capacity" in k:
        c = _safe_float(val, "%")
        result["capacity"] = round(c, 1) if c is not None else None
    elif "temperature" in k:
        result["temperature"] = _safe_float(val, "degrees C")
    elif "charge-cycles" in k:
        result["charge_cycles"] = _safe_int(val)


def _parse_text_fields(k: str, val: str, result: dict) -> None:
    if "state" in k:
        result["state"] = val
    elif "time to empty" in k:
        result["time_to_empty"] = val
    elif "time to full" in k:
        result["time_to_full"] = val
    elif "serial" in k:
        result["serial"] = val
    elif "vendor" in k:
        result["vendor"] = val
    elif "model" in k:
        result["model"] = val
    elif "technology" in k:
        result["technology"] = val
    elif "icon-name" in k or "icon_name" in k:
        result["icon_name"] = val


def _format_battery_result(info: dict[str, str]) -> dict:
    result = {
        "percentage": None,
        "state": None,
        "voltage": None,
        "voltage_min_design": None,
        "voltage_max_design": None,
        "time_to_empty": None,
        "time_to_full": None,
        "energy": None,
        "energy_full": None,
        "energy_full_design": None,
        "energy_rate": None,
        "capacity": None,
        "temperature": None,
        "serial": None,
        "vendor": None,
        "model": None,
        "technology": None,
        "charge_cycles": None,
        "icon_name": None,
        "note": "Battery info" if info else "No battery detected",
    }
    for key, value in info.items():
        k = key.lower()
        _parse_numeric_fields(k, value, result)
        _parse_text_fields(k, value, result)
    return result


def _query_battery_info() -> dict:
    # Find battery device
    battery_path = _get_upower_device() or "/org/freedesktop/UPower/devices/battery_qcom_battery"
    code, out, err = run_command(["upower", "-i", battery_path], timeout=10)
    if code != 0:
        return {"error": err, "note": "upower not available or battery not found"}
    info = _parse_upower_kv(out)
    return _format_battery_result(info)


def _collect_upower() -> dict:
    """Collect upower battery status with a 5-second TTL cache."""
    assert_not_in_running_loop("_collect_upower")
    global _battery_cache
    cached = _battery_cache
    if cached is not None and (time.monotonic() - cached[0]) < _BATTERY_CACHE_TTL:
        return dict(cached[1])

    data = _query_battery_info()
    _battery_cache = (time.monotonic(), data)
    return dict(data)


def collect_upower() -> dict:
    """Collect battery information using upower synchronously.

    WARNING: This is a synchronous blocking function executing external
    subprocesses. It must never be called directly on an active event loop;
    always offload with `await asyncio.to_thread(...)`.
    """
    assert_not_in_running_loop("collect_upower")
    return _collect_upower()


def get_battery_info() -> dict:
    """
    Get battery information using upower.
    """
    assert_not_in_running_loop("get_battery_info")
    return _collect_upower()


def get_thermal_zones() -> list[dict]:
    """
    Read thermal zones from /sys/class/thermal/.
    """
    zones = []
    thermal_dir = "/sys/class/thermal"

    if not os.path.isdir(thermal_dir):
        return [{"note": "No thermal zones available"}]

    for entry in sorted(os.listdir(thermal_dir)):
        if entry.startswith("thermal_zone"):
            zone_path = os.path.join(thermal_dir, entry)
            zone = {
                "name": entry,
                "type": "",
                "display_name": "",
                "temp_millicelsius": None,
                "temp_celsius": None,
                "warning": False,
            }

            # Read type
            type_path = os.path.join(zone_path, "type")
            if os.path.isfile(type_path):
                try:
                    with open(type_path) as f:
                        zone["type"] = f.read().strip()
                except Exception:
                    pass

            # Map to readable display name
            zone["display_name"] = THERMAL_NAME_MAP.get(zone["type"], zone["type"] or entry)

            # Read temperature
            temp_path = os.path.join(zone_path, "temp")
            if os.path.isfile(temp_path):
                try:
                    with open(temp_path) as f:
                        temp_raw = int(f.read().strip())
                        zone["temp_millicelsius"] = temp_raw
                        zone["temp_celsius"] = round(temp_raw / 1000, 1)
                        if temp_raw > 70000:
                            zone["warning"] = True
                except Exception:
                    pass

            zones.append(zone)

    return zones


def get_cpu_frequencies() -> list[dict]:
    """
    Read CPU frequencies from /sys/devices/system/cpu/.
    """
    cpu_freqs = []
    cpu_dir = "/sys/devices/system/cpu"

    if not os.path.isdir(cpu_dir):
        return [{"note": "CPU frequency info not available"}]

    for entry in sorted(os.listdir(cpu_dir)):
        if entry.startswith("cpu") and entry.isdigit():
            cpu_num = int(entry[3:])
            cpu_path = os.path.join(cpu_dir, entry)
            cpu_info = {
                "cpu": cpu_num,
                "frequency_khz": None,
                "frequency_mhz": None,
                "governor": None,
            }

            # Read current frequency
            freq_path = os.path.join(cpu_path, "cpufreq", "scaling_cur_freq")
            if os.path.isfile(freq_path):
                try:
                    with open(freq_path) as f:
                        freq = int(f.read().strip())
                        cpu_info["frequency_khz"] = freq
                        cpu_info["frequency_mhz"] = round(freq / 1000, 1)
                except Exception:
                    pass

            # Read governor
            gov_path = os.path.join(cpu_path, "cpufreq", "scaling_governor")
            if os.path.isfile(gov_path):
                try:
                    with open(gov_path) as f:
                        cpu_info["governor"] = f.read().strip()
                except Exception:
                    pass

            cpu_freqs.append(cpu_info)

    return cpu_freqs


def get_cpu_scaling_available() -> dict:
    """Get available CPU frequency governors and ranges."""
    result = {"governors": [], "min_freq": None, "max_freq": None}
    cpu0_path = "/sys/devices/system/cpu/cpu0/cpufreq"

    if os.path.isdir(cpu0_path):
        try:
            avail_path = os.path.join(cpu0_path, "scaling_available_governors")
            if os.path.isfile(avail_path):
                with open(avail_path) as f:
                    result["governors"] = f.read().strip().split()

            min_path = os.path.join(cpu0_path, "scaling_min_freq")
            max_path = os.path.join(cpu0_path, "scaling_max_freq")
            if os.path.isfile(min_path):
                with open(min_path) as f:
                    result["min_freq"] = int(f.read().strip())
            if os.path.isfile(max_path):
                with open(max_path) as f:
                    result["max_freq"] = int(f.read().strip())
        except Exception:
            pass

    return result


def get_uptime() -> dict:
    """Get system uptime from /proc/uptime."""
    uptime_sec = 0.0
    uptime_str = "Unknown"
    try:
        with open("/proc/uptime") as f:
            uptime_sec = float(f.read().strip().split()[0])
            days = int(uptime_sec // 86400)
            hours = int((uptime_sec % 86400) // 3600)
            minutes = int((uptime_sec % 3600) // 60)
            parts = []
            if days > 0:
                parts.append(f"{days}d")
            if hours > 0 or days > 0:
                parts.append(f"{hours}h")
            parts.append(f"{minutes}m")
            uptime_str = " ".join(parts)
    except Exception:
        pass
    return {
        "seconds": uptime_sec,
        "formatted": uptime_str,
    }


def set_cpu_governor(governor: str) -> dict:
    """
    Set CPU frequency scaling governor across all CPU cores (requires sudo).
    """
    clean_gov = governor.strip().lower()
    if not re.match(r"^[a-zA-Z0-9_-]+$", clean_gov) or clean_gov.startswith("-"):
        return {"success": False, "error": "Invalid governor format"}

    avail = get_cpu_scaling_available().get("governors", [])
    if avail and clean_gov not in avail:
        return {
            "success": False,
            "error": f"Governor '{clean_gov}' not supported. Available: {', '.join(avail)}",
        }

    # 1. Try cpupower command
    code, out, err = run_sudo_command(["cpupower", "frequency-set", "-g", clean_gov], timeout=10)
    if code == 0:
        return {"success": True, "governor": clean_gov, "output": out.strip()}

    # 2. Fallback to direct sysfs write
    cpu_dir = "/sys/devices/system/cpu"
    success_count = 0
    errors = []
    if os.path.isdir(cpu_dir):
        for entry in sorted(os.listdir(cpu_dir)):
            if entry.startswith("cpu") and entry[3:].isdigit():
                gov_file = os.path.join(cpu_dir, entry, "cpufreq", "scaling_governor")
                if os.path.isfile(gov_file):
                    try:
                        res = subprocess.run(
                            ["sudo", "-n", "tee", gov_file],
                            input=f"{clean_gov}\n",
                            text=True,
                            capture_output=True,
                            timeout=5,
                        )
                        c, o, e = res.returncode, res.stdout, res.stderr
                    except Exception as exc:
                        c, o, e = -1, "", str(exc)
                    if c == 0:
                        success_count += 1
                    else:
                        errors.append(f"{entry}: {e or o}")

    if success_count > 0:
        return {
            "success": True,
            "governor": clean_gov,
            "output": f"Governor '{clean_gov}' set on {success_count} CPU cores",
        }

    return {
        "success": False,
        "error": "; ".join(errors) or err or "Failed to set CPU governor",
    }
