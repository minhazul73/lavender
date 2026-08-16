"""
User and permission management.
"""
import os

from dashboard.dependencies import (
    parse_passwd_users,
    parse_groups,
    get_current_user_info,
    read_sudoers,
    visudo_check,
)


def get_users(min_uid: int = 1000) -> list[dict]:
    """Get list of human users (uid >= min_uid)."""
    return parse_passwd_users(min_uid)


def get_all_users() -> list[dict]:
    """Get all users from /etc/passwd."""
    return parse_passwd_users(0)


def get_groups() -> list[dict]:
    """Get all groups from /etc/group."""
    return parse_groups()


def get_user_groups(username: str) -> list[str]:
    """Get groups for a specific user."""
    groups = parse_groups()
    user_groups = []
    for g in groups:
        if username in g["members"]:
            user_groups.append(g["name"])
    return user_groups


def get_current_user() -> dict:
    """Get info about the current user."""
    return get_current_user_info()


def get_sudoers_info() -> dict:
    """Get sudoers configuration info."""
    sudoers_content = read_sudoers()
    visudo_ok, visudo_msg = visudo_check()
    return {
        "sudoers_available": bool(sudoers_content),
        "sudoers_content": sudoers_content,
        "visudo_ok": visudo_ok,
        "visudo_msg": visudo_msg,
    }
