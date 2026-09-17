"""
Battery, thermal, and CPU frequency management.
"""
import subprocess
import os

from dashboard.dependencies import run_command


# Thermal zone type-to-display-name mapping for readable labels
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


def get_battery_info() -> dict:
    """
    Get battery information using upower.
    """
    # Find battery device
    code, out, err = run_command(["upower", "-e"], timeout=10)
    battery_path = None
    if code == 0:
        for line in out.split("\n"):
            if "battery" in line.lower() and "line_power" not in line.lower():
                battery_path = line.strip()
                break

    if not battery_path:
        # Try the known path
        battery_path = "/org/freedesktop/UPower/devices/battery_qcom_battery"

    # Get detailed info
    code, out, err = run_command(["upower", "-i", battery_path], timeout=10)
    if code != 0:
        return {"error": err, "note": "upower not available or battery not found"}

    info = {}
    current_key = None
    for line in out.split("\n"):
        line = line.strip()
        if not line:
            continue

        if ":" in line:
            parts = line.split(":", 1)
            key = parts[0].strip()
            value = parts[1].strip() if len(parts) > 1 else ""
            if value:
                info[key] = value
                current_key = None
            else:
                current_key = key
                info[current_key] = ""
        elif current_key:
            value = line.strip()
            if value:
                if info[current_key]:
                    info[current_key] += " " + value
                else:
                    info[current_key] = value

    # Parse key fields — match upower's actual key names
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
        "capacity": None,  # percentage of design capacity (upower: "capacity: 100%")
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
        if "percentage" in key.lower():
            try:
                result["percentage"] = int(value.replace("%", "").strip())
            except (ValueError, AttributeError):
                pass
        elif "state" in key.lower():
            result["state"] = value
        elif key.lower() == "voltage":
            try:
                result["voltage"] = float(value.replace("V", "").strip())
            except (ValueError, AttributeError):
                pass
        elif "voltage-min-design" in key.lower():
            try:
                result["voltage_min_design"] = float(value.replace("V", "").strip())
            except (ValueError, AttributeError):
                pass
        elif "voltage-max-design" in key.lower():
            try:
                result["voltage_max_design"] = float(value.replace("V", "").strip())
            except (ValueError, AttributeError):
                pass
        elif "time to empty" in key.lower():
            result["time_to_empty"] = value
        elif "time to full" in key.lower():
            result["time_to_full"] = value
        elif key.lower() == "energy":
            try:
                result["energy"] = float(value.replace("Wh", "").strip())
            except (ValueError, AttributeError):
                pass
        elif "energy-full" in key.lower() and "design" not in key.lower():
            try:
                result["energy_full"] = float(value.replace("Wh", "").strip())
            except (ValueError, AttributeError):
                pass
        elif "energy-full-design" in key.lower():
            try:
                result["energy_full_design"] = float(value.replace("Wh", "").strip())
            except (ValueError, AttributeError):
                pass
        elif "energy-rate" in key.lower():
            try:
                result["energy_rate"] = float(value.replace("W", "").strip())
            except (ValueError, AttributeError):
                pass
        elif "capacity" in key.lower():
            try:
                result["capacity"] = round(float(value.replace("%", "").strip()), 1)
            except (ValueError, AttributeError):
                pass
        elif "temperature" in key.lower():
            try:
                result["temperature"] = float(value.replace("degrees C", "").strip())
            except (ValueError, AttributeError):
                pass
        elif "serial" in key.lower():
            result["serial"] = value
        elif "vendor" in key.lower():
            result["vendor"] = value
        elif "model" in key.lower() or "native path" in key.lower():
            if "model" in key.lower():
                result["model"] = value
        elif "technology" in key.lower():
            result["technology"] = value
        elif "charge-cycles" in key.lower():
            try:
                result["charge_cycles"] = int(value.strip())
            except (ValueError, AttributeError):
                pass
        elif "icon-name" in key.lower() or "icon_name" in key.lower():
            result["icon_name"] = value

    return result


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
                    with open(type_path, "r") as f:
                        zone["type"] = f.read().strip()
                except Exception:
                    pass

            # Map to readable display name
            zone["display_name"] = THERMAL_NAME_MAP.get(zone["type"], zone["type"] or entry)

            # Read temperature
            temp_path = os.path.join(zone_path, "temp")
            if os.path.isfile(temp_path):
                try:
                    with open(temp_path, "r") as f:
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
                    with open(freq_path, "r") as f:
                        freq = int(f.read().strip())
                        cpu_info["frequency_khz"] = freq
                        cpu_info["frequency_mhz"] = round(freq / 1000, 1)
                except Exception:
                    pass

            # Read governor
            gov_path = os.path.join(cpu_path, "cpufreq", "scaling_governor")
            if os.path.isfile(gov_path):
                try:
                    with open(gov_path, "r") as f:
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
                with open(avail_path, "r") as f:
                    result["governors"] = f.read().strip().split()

            min_path = os.path.join(cpu0_path, "scaling_min_freq")
            max_path = os.path.join(cpu0_path, "scaling_max_freq")
            if os.path.isfile(min_path):
                with open(min_path, "r") as f:
                    result["min_freq"] = int(f.read().strip())
            if os.path.isfile(max_path):
                with open(max_path, "r") as f:
                    result["max_freq"] = int(f.read().strip())
        except Exception:
            pass

    return result
