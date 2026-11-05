from typing import Any

from pydantic import BaseModel


class ServiceItem(BaseModel):
    unit: str
    load: str | None = None
    active: str | None = None
    sub: str | None = None
    description: str | None = None
    scope: str | None = None


class ServicesListResponse(BaseModel):
    services: list[dict[str, Any]]
    count: int


class ServiceActionResponse(BaseModel):
    success: bool
    action: str
    service: str
    user: bool
    output: str | None = None


class ProcessItem(BaseModel):
    pid: int
    user: str
    cpu: float
    mem: float
    command: str
    name: str


class ProcessesOverviewResponse(BaseModel):
    processes: list[dict[str, Any]]
    load: dict[str, Any]
    memory: dict[str, Any]


class KillProcessResponse(BaseModel):
    action: str
    pid: int
    success: bool
    output: str | None = None


class SystemLogsResponse(BaseModel):
    logs: list[str]
    count: int
