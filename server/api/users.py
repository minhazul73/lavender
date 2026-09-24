"""
User Management and Access Control API routes for Lavender.
Provides user inspection, active sessions, SSH key management, groups editing, and password updates.
"""
import asyncio
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException

from server.auth.bridge import run_sudo_async
from server.auth.deps import require_admin, require_session
from server.auth.session import UserSession
from server.core.executor import get_executor
from server.dependencies import parse_all_passwd_users, parse_groups
from server.services.users import (
    add_user_ssh_key,
    delete_user_ssh_key,
    get_active_sessions,
    get_categorized_groups,
    get_current_user,
    get_human_users,
    get_login_history,
    get_security_posture,
    get_sudoers_info,
    get_system_users,
    get_user_groups,
    get_user_ssh_keys,
)

router = APIRouter()


@router.get("", summary="Get users, groups, and access control overview")
@router.get("/", include_in_schema=False)
@router.get("/users", include_in_schema=False)
async def api_users(session: UserSession = Depends(require_session)):
    """Get user, session, group, and access control information."""
    username = session.username if session else None
    human_users = await asyncio.to_thread(get_human_users, username)
    system_users = await asyncio.to_thread(get_system_users)
    categorized_groups = await asyncio.to_thread(get_categorized_groups)
    active_sessions = await asyncio.to_thread(get_active_sessions)
    login_history = await asyncio.to_thread(get_login_history, 10)
    security_posture = await asyncio.to_thread(get_security_posture)
    current_user_info = await asyncio.to_thread(get_current_user)
    sudoers_info = await asyncio.to_thread(get_sudoers_info)

    active_sessions_count = len(active_sessions)
    human_users_count = len(human_users)
    total_ssh_keys = sum(u.get("ssh_keys_count", 0) for u in human_users)
    is_elevated = session.is_elevated() if session else False

    return {
        "human_users": human_users,
        "system_users": system_users,
        "groups_categorized": categorized_groups,
        "active_sessions": active_sessions,
        "login_history": login_history,
        "security": security_posture,
        "metrics": {
            "active_sessions_count": active_sessions_count,
            "human_users_count": human_users_count,
            "total_ssh_keys": total_ssh_keys,
            "is_elevated": is_elevated,
        },
        # Backwards compatibility
        "users": human_users,
        "all_users": system_users,
        "groups": categorized_groups,
        "current_user": current_user_info,
        "sudoers": sudoers_info,
    }


@router.post("/session/terminate", summary="Terminate active user session")
@router.post("/users/session/terminate", include_in_schema=False)
async def api_terminate_session(
    payload: dict,
    session: UserSession = Depends(require_admin),
):
    """Terminate an active terminal or SSH session (Admin gated)."""
    tty = payload.get("tty", "").strip()
    if not tty:
        raise HTTPException(status_code=400, detail="Missing TTY name")
    clean_tty = os.path.basename(tty)
    code, out, err = await run_sudo_async(["pkill", "-9", "-t", clean_tty])
    if code != 0 and "No such process" in (out + err):
        await run_sudo_async(["loginctl", "terminate-session", clean_tty])
    return {"success": True, "message": f"Session on {clean_tty} terminated"}


@router.get("/{username}/ssh-keys", summary="Get user public SSH keys")
@router.get("/users/{username}/ssh-keys", include_in_schema=False)
async def api_get_ssh_keys(
    username: str,
    session: UserSession = Depends(require_session),
):
    """Get installed public SSH keys for a user."""
    if session.username != username and not session.is_elevated():
        raise HTTPException(status_code=403, detail="Admin privileges required to view other users' keys")
    keys = await asyncio.to_thread(get_user_ssh_keys, username)
    return {"username": username, "keys": keys}


@router.post("/{username}/ssh-keys", summary="Add public SSH key to user")
@router.post("/users/{username}/ssh-keys", include_in_schema=False)
async def api_add_ssh_key(
    username: str,
    payload: dict,
    session: UserSession = Depends(require_session),
):
    """Add a public SSH key to a user's authorized_keys."""
    if session.username != username and not session.is_elevated():
        raise HTTPException(status_code=403, detail="Admin privileges required to modify other users' keys")
    key = payload.get("key", "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="Key content is required")
    success = await asyncio.to_thread(add_user_ssh_key, username, key)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid public key format or failed to write")
    return {"success": True, "message": "SSH key added successfully"}


@router.delete("/{username}/ssh-keys/{key_index}", summary="Delete public SSH key")
@router.delete("/users/{username}/ssh-keys/{key_index}", include_in_schema=False)
async def api_delete_ssh_key(
    username: str,
    key_index: int,
    session: UserSession = Depends(require_session),
):
    """Delete a public SSH key by index."""
    if session.username != username and not session.is_elevated():
        raise HTTPException(status_code=403, detail="Admin privileges required to modify other users' keys")
    success = await asyncio.to_thread(delete_user_ssh_key, username, key_index)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete key")
    return {"success": True, "message": "SSH key removed"}


@router.post("/{username}/groups", summary="Update secondary groups for user")
@router.post("/users/{username}/groups", include_in_schema=False)
async def api_update_user_groups(
    username: str,
    payload: dict,
    session: UserSession = Depends(require_admin),
):
    """Update secondary groups for a user safely (Admin gated)."""
    groups = payload.get("groups", [])
    if not isinstance(groups, list):
        raise HTTPException(status_code=400, detail="Groups must be a list of group names")

    # Verify user exists
    all_users = parse_all_passwd_users()
    if not any(u["name"] == username for u in all_users):
        raise HTTPException(status_code=404, detail=f"User '{username}' does not exist")

    # Query system groups so we never pass a non-existent group
    system_groups = {g["name"] for g in parse_groups()}
    valid_requested = {g for g in groups if g in system_groups}

    # Preserve unmanaged secondary groups that the user is already in
    current_user_groups = set(get_user_groups(username))
    editable_groups = {
        "wheel", "sudo", "docker", "audio", "video",
        "netdev", "plugdev", "dialout", "input", "camera", "disk", "kvm"
    }
    unmanaged_groups = {g for g in current_user_groups if g not in editable_groups and g in system_groups}

    final_groups = sorted(list(unmanaged_groups | valid_requested))
    groups_arg = ",".join(final_groups)

    # 1. Try standard usermod -G
    code, out, err = await run_sudo_async(["usermod", "-G", groups_arg, username])
    if code != 0:
        # Fallback for Alpine / BusyBox: addgroup and delgroup
        to_add = valid_requested - current_user_groups
        to_remove = (current_user_groups & editable_groups) - valid_requested
        err_messages = []

        for g in to_add:
            c, o, e = await run_sudo_async(["addgroup", username, g])
            if c != 0:
                c2, o2, e2 = await run_sudo_async(["gpasswd", "-a", username, g])
                if c2 != 0:
                    err_messages.append(f"add to {g}: {e or e2}")

        for g in to_remove:
            c, o, e = await run_sudo_async(["delgroup", username, g])
            if c != 0:
                c2, o2, e2 = await run_sudo_async(["gpasswd", "-d", username, g])
                if c2 != 0:
                    err_messages.append(f"remove from {g}: {e or e2}")

        if err_messages:
            raise HTTPException(status_code=500, detail=f"Failed to update groups: {'; '.join(err_messages)}")

    return {"success": True, "message": f"Updated groups for {username}", "groups": final_groups}


@router.post("/{username}/password", summary="Change user password")
@router.post("/users/{username}/password", include_in_schema=False)
async def api_change_password(
    username: str,
    payload: dict,
    session: UserSession = Depends(require_session),
):
    """Change user password (Self or Admin gated)."""
    if session.username != username and not session.is_elevated():
        raise HTTPException(status_code=403, detail="Admin privileges required")
    new_pass = payload.get("new_password", "").strip()
    if not new_pass or len(new_pass) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")

    # Update password via chpasswd using executor run_with_stdin
    executor = get_executor()
    res = await executor.run_with_stdin(
        ["sudo", "-n", "chpasswd"],
        stdin_data=f"{username}:{new_pass}\n",
        timeout=10,
    )
    if res.returncode != 0:
        err = res.stderr or res.stdout
        raise HTTPException(status_code=500, detail=f"Failed to change password: {err}")
    return {"success": True, "message": f"Password successfully updated for {username}"}
