from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class PackageItem(BaseModel):
    name: str
    version: Optional[str] = None
    description: Optional[str] = None
    installed: Optional[bool] = None
    upgradable: Optional[bool] = None
    new_version: Optional[str] = None


class PackagesOverviewResponse(BaseModel):
    backend: str
    backend_name: str
    backend_short: str
    installed_count: int
    upgradable_count: int
    upgradable: List[Dict[str, Any]]
    installed: List[Dict[str, Any]]


class PackageActionResponse(BaseModel):
    action: str
    package: Optional[str] = None
    success: bool
    output: Optional[str] = None
