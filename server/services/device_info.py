"""
System and device information detection service for Lavender.
Dynamically discovers hardware model, OS distribution, kernel, architecture, and hostname.
Avoids hardcoding any specific phone or board model.
"""
import os
import platform
import subprocess
import socket
from functools import lru_cache
from typing import Dict, Any


def get_device_model() -> str:
    """
    Retrieve the hardware/board device model.
    Priority order:
    1. Linux Device Tree (ARM mobile/smartphones like Redmi Note 7, SBCs):
       /sys/firmware/devicetree/base/model or /proc/device-tree/model
    2. postmarketOS / Alpine deviceinfo:
       /etc/deviceinfo (deviceinfo_name)
    3. DMI/SMBIOS product name (x86_64 laptops, PCs, servers):
       /sys/class/dmi/id/product_name or /sys/devices/virtual/dmi/id/product_name
    4. hostnamectl (Hardware Model / Model)
    5. /etc/machine-info (PRETTY_HOSTNAME)
    6. System hostname / generic fallback
    """
    # 1. Device Tree (ARM / Smartphones / SBCs)
    for dt_path in ("/sys/firmware/devicetree/base/model", "/proc/device-tree/model"):
        if os.path.exists(dt_path):
            try:
                with open(dt_path, "rb") as f:
                    val = f.read().decode("utf-8", errors="ignore").strip().rstrip("\x00")
                if val:
                    return val
            except Exception:
                pass

    # 2. postmarketOS / Alpine deviceinfo
    if os.path.exists("/etc/deviceinfo"):
        try:
            with open("/etc/deviceinfo", "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("deviceinfo_name="):
                        val = line.split("=", 1)[1].strip().strip("\"'")
                        if val:
                            return val
        except Exception:
            pass

    # 3. DMI / SMBIOS (Laptops, PCs, Desktops, Servers)
    for dmi_path in (
        "/sys/class/dmi/id/product_name",
        "/sys/devices/virtual/dmi/id/product_name",
        "/sys/class/dmi/id/board_name",
    ):
        if os.path.exists(dmi_path):
            try:
                with open(dmi_path, "r", encoding="utf-8", errors="ignore") as f:
                    val = f.read().strip()
                if val and val.lower() not in (
                    "none",
                    "default string",
                    "system product name",
                    "to be filled by o.e.m.",
                    "o.e.m.",
                    "type1productconfigid",
                ):
                    # Clean up repeated product model suffixes (e.g. Model_Model)
                    if "_" in val:
                        parts = val.split("_")
                        if len(parts) == 2 and parts[0].endswith(parts[1]):
                            val = parts[0]
                    return val
            except Exception:
                pass

    # 4. hostnamectl (systemd systems)
    try:
        out = subprocess.check_output(
            ["hostnamectl"], text=True, stderr=subprocess.DEVNULL, timeout=1.5
        )
        for line in out.splitlines():
            line_str = line.strip()
            for prefix in ("hardware model:", "model:", "chassis:"):
                if line_str.lower().startswith(prefix):
                    val = line_str.split(":", 1)[1].strip()
                    if val and val.lower() not in ("none", "unknown"):
                        return val
    except Exception:
        pass

    # 5. /etc/machine-info (systemd PRETTY_HOSTNAME)
    if os.path.exists("/etc/machine-info"):
        try:
            with open("/etc/machine-info", "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.strip().startswith("PRETTY_HOSTNAME="):
                        val = line.strip().split("=", 1)[1].strip().strip("\"'")
                        if val:
                            return val
        except Exception:
            pass

    # 6. Fallback to hostname or generic
    try:
        host = socket.gethostname()
        if host and host not in ("localhost", "localhost.localdomain"):
            return host
    except Exception:
        pass

    return platform.node() or "Linux Device"


def get_os_info() -> Dict[str, str]:
    """
    Retrieve OS distribution details.
    Parses /etc/os-release or /usr/lib/os-release.
    """
    data: Dict[str, str] = {}
    for rel_path in ("/etc/os-release", "/usr/lib/os-release"):
        if os.path.exists(rel_path):
            try:
                with open(rel_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line and not line.startswith("#"):
                            k, v = line.split("=", 1)
                            data[k.strip()] = v.strip().strip("\"'")
                if data:
                    break
            except Exception:
                pass

    name = data.get("NAME") or platform.system() or "Linux"
    pretty_name = data.get("PRETTY_NAME") or name
    version_id = data.get("VERSION_ID") or data.get("VERSION") or ""
    os_id = data.get("ID") or name.lower()

    return {
        "name": name,
        "pretty_name": pretty_name,
        "version": version_id,
        "id": os_id,
    }


@lru_cache(maxsize=1)
def get_system_info() -> Dict[str, Any]:
    """
    Get cached system and device metadata for templates and API responses.
    Result is cached since hardware model, OS name, and architecture do not
    change during runtime.
    """
    model = get_device_model()
    os_info = get_os_info()

    return {
        "model": model,
        "os_name": os_info["name"],
        "os_pretty": os_info["pretty_name"],
        "os_version": os_info["version"],
        "os_id": os_info["id"],
        "kernel": platform.release(),
        "arch": platform.machine(),
        "hostname": socket.gethostname(),
    }
