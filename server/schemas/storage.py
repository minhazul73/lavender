from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class StorageDiskItem(BaseModel):
    filesystem: Optional[str] = None
    size: Optional[str] = None
    used: Optional[str] = None
    available: Optional[str] = None
    use_percent: Optional[str] = None
    mount_point: Optional[str] = None


class StorageOverviewResponse(BaseModel):
    disks: List[Dict[str, Any]]


class UnmountResponse(BaseModel):
    success: bool
    mount_point: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None
