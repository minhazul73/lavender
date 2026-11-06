from typing import Any

from pydantic import BaseModel


class StorageDiskItem(BaseModel):
    filesystem: str | None = None
    size: str | None = None
    used: str | None = None
    available: str | None = None
    use_percent: str | None = None
    mount_point: str | None = None


class StorageOverviewResponse(BaseModel):
    disks: list[dict[str, Any]]


class UnmountResponse(BaseModel):
    success: bool
    mount_point: str | None = None
    message: str | None = None
    error: str | None = None


class SaveFileRequest(BaseModel):
    path: str
    content: str


class CreateDirRequest(BaseModel):
    path: str
    name: str


class CreateFileRequest(BaseModel):
    path: str
    name: str
    content: str | None = ""


class RenameRequest(BaseModel):
    old_path: str
    new_name: str


class DeleteFilesRequest(BaseModel):
    paths: list[str]
