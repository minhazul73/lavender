from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ServiceItem(BaseModel):
    unit: str
    load: Optional[str] = None
    active: Optional[str] = None
    sub: Optional[str] = None
    description: Optional[str] = None
    scope: Optional[str] = None


class ServicesListResponse(BaseModel):
    services: List[Dict[str, Any]]
    count: int


class ServiceActionResponse(BaseModel):
    success: bool
    action: str
    service: str
    user: bool
    output: Optional[str] = None


class ProcessItem(BaseModel):
    pid: int
    user: str
    cpu: float
    mem: float
    command: str
    name: str


class ProcessesOverviewResponse(BaseModel):
    processes: List[Dict[str, Any]]
    load: Dict[str, Any]
    memory: Dict[str, Any]


class KillProcessResponse(BaseModel):
    action: str
    pid: int
    success: bool
    output: Optional[str] = None


class SystemLogsResponse(BaseModel):
    logs: List[str]
    count: int
