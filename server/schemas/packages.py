from typing import Any

from pydantic import BaseModel


class PackageItem(BaseModel):
    name: str
    version: str | None = None
    description: str | None = None
    installed: bool | None = None
    upgradable: bool | None = None
    new_version: str | None = None


class PackagesOverviewResponse(BaseModel):
    backend: str
    backend_name: str
    backend_short: str
    installed_count: int
    upgradable_count: int
    upgradable: list[dict[str, Any]]
    installed: list[dict[str, Any]]


class PackageActionResponse(BaseModel):
    action: str
    package: str | None = None
    success: bool
    output: str | None = None
