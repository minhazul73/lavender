from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PowerActionResponse(BaseModel):
    action: str
    success: bool
    output: Optional[str] = None


class PowerStateResponse(BaseModel):
    active_governor: str
    available_governors: List[str]
    scheduled: Optional[Dict[str, Any]] = None


class SchedulePowerRequest(BaseModel):
    action: str = Field(..., description="Action to schedule: 'reboot' or 'poweroff'")
    minutes: int = Field(..., ge=1, le=1440, description="Minutes until action executes")
    message: Optional[str] = Field(default="Scheduled from Lavender", description="Broadcast warning message")
