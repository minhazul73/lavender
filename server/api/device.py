"""
Device and Hardware API routes for Lavender.
Provides system model metadata, kernel version, battery, thermal sensors, and uptime stats.
"""
from typing import Optional
from fastapi import APIRouter, Depends

from server.auth.deps import get_current_session
from server.auth.session import UserSession
from server.services.battery import (
    get_battery_info,
    get_cpu_frequencies,
    get_cpu_scaling_available,
    get_thermal_zones,
    get_uptime,
)
from server.services.device_info import get_system_info

router = APIRouter()


@router.get("/info", summary="Get system hardware, OS, and kernel info")
@router.get("/device/info", include_in_schema=False)
async def api_device_info(session: Optional[UserSession] = Depends(get_current_session)):
    """Get dynamic system, hardware model, OS, and kernel metadata."""
    return get_system_info()


@router.get("/battery", summary="Get battery, thermal sensors, and CPU frequencies")
@router.get("/device/battery", include_in_schema=False)
async def api_battery(session: Optional[UserSession] = Depends(get_current_session)):
    """Get battery, thermal zones, CPU frequency, and system uptime."""
    return {
        "battery": get_battery_info(),
        "thermal": get_thermal_zones(),
        "cpu_freq": get_cpu_frequencies(),
        "cpu_scaling": get_cpu_scaling_available(),
        "uptime": get_uptime(),
    }
