from typing import Any

from pydantic import BaseModel, Field


class PowerActionResponse(BaseModel):
    action: str
    success: bool
    output: str | None = None


class PowerStateResponse(BaseModel):
    active_governor: str
    available_governors: list[str]
    scheduled: dict[str, Any] | None = None


class SchedulePowerRequest(BaseModel):
    action: str = Field(..., description="Action to schedule: 'reboot' or 'poweroff'")
    minutes: int = Field(..., ge=1, le=1440, description="Minutes until action executes")
    message: str | None = Field(default="Scheduled from Lavender", description="Broadcast warning message")
