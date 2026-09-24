"""
Storage and Disks API routes for Lavender.
Provides filesystem usage inspection, mount information, and unmounting operations.
"""
import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from server.auth.deps import get_current_session, require_admin
from server.auth.session import UserSession
from server.services.storage import get_disk_usage, unmount

router = APIRouter()


@router.get("", summary="Get disk and mount usage information")
@router.get("/", include_in_schema=False)
async def api_storage(session: Optional[UserSession] = Depends(get_current_session)):
    """Get disk usage, partitions, and mounted filesystems."""
    return {
        "disks": get_disk_usage(),
    }


@router.post("/unmount", summary="Unmount filesystem")
async def api_unmount(
    mount_point: str = Query(..., description="Mount point to unmount"),
    session: UserSession = Depends(require_admin),
):
    """Unmount a filesystem (requires administrative privileges)."""
    res = await asyncio.to_thread(unmount, mount_point)
    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error", "Unmount failed"))
    return res
