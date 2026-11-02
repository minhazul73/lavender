from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class SystemInfoResponse(BaseModel):
    hostname: Optional[str] = None
    distro: Optional[str] = None
    os_name: Optional[str] = None
    kernel: Optional[str] = None
    arch: Optional[str] = None
    uptime: Optional[str] = None
    hardware_model: Optional[str] = None
    device_tree_model: Optional[str] = None
    cpu_model: Optional[str] = None
    cpu_cores: Optional[int] = None
    total_memory: Optional[str] = None
    is_chroot: Optional[bool] = False


class BatteryStatus(BaseModel):
    present: bool
    status: Optional[str] = None
    capacity: Optional[int] = None
    health: Optional[str] = None
    technology: Optional[str] = None
    voltage_now: Optional[float] = None
    current_now: Optional[float] = None
    power_now: Optional[float] = None


class DeviceStatsResponse(BaseModel):
    battery: Dict[str, Any]
    thermal: List[Dict[str, Any]]
    cpu_freq: List[Dict[str, Any]]
    cpu_scaling: Dict[str, Any]
    uptime: Dict[str, Any]
