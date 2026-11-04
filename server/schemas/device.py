from typing import Any

from pydantic import BaseModel


class SystemInfoResponse(BaseModel):
    hostname: str | None = None
    distro: str | None = None
    os_name: str | None = None
    kernel: str | None = None
    arch: str | None = None
    uptime: str | None = None
    hardware_model: str | None = None
    device_tree_model: str | None = None
    cpu_model: str | None = None
    cpu_cores: int | None = None
    total_memory: str | None = None
    is_chroot: bool | None = False


class BatteryStatus(BaseModel):
    present: bool
    status: str | None = None
    capacity: int | None = None
    health: str | None = None
    technology: str | None = None
    voltage_now: float | None = None
    current_now: float | None = None
    power_now: float | None = None


class DeviceStatsResponse(BaseModel):
    battery: dict[str, Any]
    thermal: list[dict[str, Any]]
    cpu_freq: list[dict[str, Any]]
    cpu_scaling: dict[str, Any]
    uptime: dict[str, Any]
