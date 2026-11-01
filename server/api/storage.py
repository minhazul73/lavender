"""
Storage and Filesystem Browser API routes for Lavender.
Provides filesystem usage inspection, mount information, unmounting operations,
and a convenient file explorer with preview, editing, file creation, rename, delete,
and file upload capabilities.
"""
import asyncio
import os
import shutil
import mimetypes
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from fastapi.responses import FileResponse

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
    canonical_path = files_service.sanitize_path(path)
    if not os.path.isfile(canonical_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    if not os.access(canonical_path, os.R_OK) and not is_session_admin(session):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Read permission denied")

    filename = os.path.basename(canonical_path)
    mime_type, _ = mimetypes.guess_type(canonical_path)
    media_type = mime_type or "application/octet-stream"

    return FileResponse(
        path=canonical_path,
        media_type=media_type,
        filename=filename,
        content_disposition_type="attachment" if download else "inline",
    )


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
    canonical_dir = files_service.sanitize_path(path)
    if not os.path.isdir(canonical_dir):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Destination is not a directory")

    is_admin = is_session_admin(session)
    is_writable = os.access(canonical_dir, os.W_OK)
    if not is_writable and not is_admin:
        detail_msg = "Permission denied to write to destination directory"
        if session and session.can_elevate():
            detail_msg = "Administrative elevation required to upload files to this directory."
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail_msg)

    from server.dependencies import run_sudo_command
    import tempfile

    uploaded = []
    for file in files:
        safe_filename = os.path.basename(file.filename or "uploaded_file")
        if not safe_filename or safe_filename in (".", ".."):
            continue

        dest_file_path = os.path.join(canonical_dir, safe_filename)
        try:
            if is_writable:
                with open(dest_file_path, "wb") as f_out:
                    shutil.copyfileobj(file.file, f_out)
            else:
                with tempfile.NamedTemporaryFile("wb", delete=False) as tf:
                    shutil.copyfileobj(file.file, tf)
                    tmp_name = tf.name
                code, out, err = run_sudo_command(["cp", "-f", tmp_name, dest_file_path])
                if code == 0:
                    run_sudo_command(["chmod", "644", dest_file_path])
                if os.path.exists(tmp_name):
                    try:
                        os.remove(tmp_name)
                    except Exception:
                        pass
                if code != 0:
                    raise RuntimeError(f"Privileged upload failed: {err or out}")
            uploaded.append(safe_filename)
        finally:
            await file.close()

    return {"success": True, "uploaded": uploaded, "count": len(uploaded)}
