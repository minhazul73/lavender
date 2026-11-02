"""
Storage and Filesystem Browser API routes for Lavender.
Provides filesystem usage inspection, mount information, unmounting operations,
and a convenient file explorer with preview, editing, file creation, rename, delete,
and file upload capabilities.
"""
import asyncio
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from fastapi.responses import StreamingResponse

from server.auth.deps import get_current_session, require_admin, require_session
from server.auth.session import UserSession
from server.services.storage import get_disk_usage, unmount
from server.services import files as files_service
from server.schemas.storage import (
    SaveFileRequest,
    CreateDirRequest,
    CreateFileRequest,
    RenameRequest,
    DeleteFilesRequest,
)

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


def is_session_admin(session: Optional[UserSession]) -> bool:
    """Check if session is currently elevated or has admin status."""
    if not session:
        return False
    return bool(session.is_elevated())


def _handle_fs_error(
    exc: Exception,
    session: "Optional[UserSession]",
    is_admin: bool,
    elevation_msg: str,
) -> None:
    """
    Translate filesystem exceptions to appropriate HTTPException responses.
    Raises an HTTPException matching the exception type.
    """
    if isinstance(exc, FileNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, (IsADirectoryError, NotADirectoryError, ValueError)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, FileExistsError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, PermissionError):
        detail_msg = str(exc)
        if session and session.can_elevate() and not is_admin:
            detail_msg = elevation_msg
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail_msg)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
    )


@router.get("/files", summary="List files and directories in a path")
async def api_list_files(
    path: Optional[str] = Query(None, description="Path to list (defaults to user home)"),
    show_hidden: bool = Query(False, description="Whether to include hidden dotfiles"),
    sort_by: str = Query("name", description="Property to sort by (name, size, modified)"),
    order: str = Query("asc", description="Sort order (asc or desc)"),
    session: Optional[UserSession] = Depends(get_current_session),
):
    """List directory contents with rich file metadata and disk usage."""
    user_home = session.home if session else None
    is_admin = is_session_admin(session)
    try:
        data = await asyncio.to_thread(
            files_service.list_directory,
            path=path,
            show_hidden=show_hidden,
            sort_by=sort_by,
            order=order,
            user_home=user_home,
            is_admin=is_admin,
        )
        return data
    except Exception as e:
        _handle_fs_error(
            e, session, is_admin,
            "Administrative elevation required to access this directory.",
        )


@router.get("/bookmarks", summary="Get quick navigation bookmarks and drive shortcuts")
async def api_get_bookmarks(session: Optional[UserSession] = Depends(get_current_session)):
    """Get quick access directories and mounted disk shortcuts."""
    user_home = session.home if session else None
    bookmarks = await asyncio.to_thread(files_service.get_quick_bookmarks, user_home=user_home)
    disks = await asyncio.to_thread(get_disk_usage)
    return {
        "bookmarks": bookmarks,
        "disks": disks,
    }


@router.get("/file/view", summary="Preview or read text file content")
async def api_view_file(
    path: str = Query(..., description="Absolute path to file"),
    session: Optional[UserSession] = Depends(get_current_session),
):
    """Read file content and metadata for preview or code editor."""
    is_admin = is_session_admin(session)
    try:
        data = await asyncio.to_thread(files_service.read_file_preview, path=path, is_admin=is_admin)
        return data
    except Exception as e:
        _handle_fs_error(
            e, session, is_admin,
            "Administrative elevation required to read this file.",
        )


@router.get("/file/raw", summary="Stream raw file for download or media preview")
async def api_raw_file(
    path: str = Query(..., description="Absolute path to file"),
    download: bool = Query(False, description="Force file download attachment"),
    session: Optional[UserSession] = Depends(get_current_session),
):
    """Stream raw file content (for inline image/video display or download)."""
    is_admin = is_session_admin(session)
    try:
        info = await asyncio.to_thread(files_service.get_raw_file_stream, path=path, is_admin=is_admin)
        disposition = "attachment" if download else "inline"
        return StreamingResponse(
            info["stream"](),
            media_type=info["media_type"],
            headers={"Content-Disposition": f'{disposition}; filename="{info["filename"]}"'},
        )
    except Exception as e:
        _handle_fs_error(e, session, is_admin, "Read permission denied.")


@router.post("/file/save", summary="Save edited file content")
async def api_save_file(
    req: SaveFileRequest,
    session: Optional[UserSession] = Depends(get_current_session),
):
    """Save updated text content to an existing file."""
    is_admin = is_session_admin(session)
    try:
        res = await asyncio.to_thread(
            files_service.save_file_content,
            path=req.path,
            content=req.content,
            is_admin=is_admin,
        )
        return res
    except Exception as e:
        _handle_fs_error(
            e, session, is_admin,
            "Administrative elevation required to save changes to this file.",
        )


@router.post("/mkdir", summary="Create a new folder")
async def api_mkdir(
    req: CreateDirRequest,
    session: Optional[UserSession] = Depends(get_current_session),
):
    """Create a new directory inside target path."""
    is_admin = is_session_admin(session)
    try:
        res = await asyncio.to_thread(
            files_service.make_directory,
            parent_path=req.path,
            name=req.name,
            is_admin=is_admin,
        )
        return res
    except Exception as e:
        _handle_fs_error(
            e, session, is_admin,
            "Administrative elevation required to create folder in this path.",
        )


@router.post("/file/create", summary="Create a new file")
async def api_create_file(
    req: CreateFileRequest,
    session: Optional[UserSession] = Depends(get_current_session),
):
    """Create a new file with optional content."""
    is_admin = is_session_admin(session)
    try:
        res = await asyncio.to_thread(
            files_service.create_new_file,
            parent_path=req.path,
            name=req.name,
            content=req.content or "",
            is_admin=is_admin,
        )
        return res
    except Exception as e:
        _handle_fs_error(
            e, session, is_admin,
            "Administrative elevation required to create file in this path.",
        )


@router.post("/rename", summary="Rename a file or folder")
async def api_rename(
    req: RenameRequest,
    session: Optional[UserSession] = Depends(get_current_session),
):
    """Rename a file or folder."""
    is_admin = is_session_admin(session)
    try:
        res = await asyncio.to_thread(
            files_service.rename_entry,
            old_path=req.old_path,
            new_name=req.new_name,
            is_admin=is_admin,
        )
        return res
    except Exception as e:
        _handle_fs_error(
            e, session, is_admin,
            "Administrative elevation required to rename in this path.",
        )


@router.post("/delete", summary="Delete files or folders")
async def api_delete(
    req: DeleteFilesRequest,
    session: Optional[UserSession] = Depends(get_current_session),
):
    """Delete one or more files/folders safely."""
    is_admin = is_session_admin(session)
    try:
        res = await asyncio.to_thread(files_service.delete_entries, paths=req.paths, is_admin=is_admin)
        return res
    except Exception as e:
        _handle_fs_error(
            e, session, is_admin,
            "Administrative elevation required to delete in this path.",
        )


@router.post("/upload", summary="Upload one or more files to a directory")
async def api_upload_files(
    path: str = Form(..., description="Destination directory path"),
    files: List[UploadFile] = File(..., description="Files to upload"),
    session: Optional[UserSession] = Depends(get_current_session),
):
    """Upload files directly into the specified directory."""
    is_admin = is_session_admin(session)
    files_data = [(f.filename or "uploaded_file", f.file) for f in files]
    try:
        uploaded = await asyncio.to_thread(
            files_service.save_uploaded_files,
            dest_dir=path,
            files_data=files_data,
            is_admin=is_admin,
        )
        return {"success": True, "uploaded": uploaded, "count": len(uploaded)}
    except Exception as e:
        _handle_fs_error(
            e,
            session,
            is_admin,
            "Administrative elevation required to upload files to this directory.",
        )
    finally:
        for file in files:
            await file.close()
