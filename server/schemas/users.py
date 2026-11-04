from typing import Any

from pydantic import BaseModel, Field


class TerminateSessionRequest(BaseModel):
    tty: str = Field(..., min_length=1, description="TTY name to terminate")


class AddSshKeyRequest(BaseModel):
    key: str = Field(..., min_length=10, description="Public SSH key string")


class UpdateUserGroupsRequest(BaseModel):
    groups: list[str] = Field(..., description="Target list of secondary group names")


class ChangePasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=4, description="New user password")


class UsersOverviewResponse(BaseModel):
    human_users: list[dict[str, Any]]
    system_users: list[dict[str, Any]]
    groups_categorized: dict[str, Any]
    active_sessions: list[dict[str, Any]]
    login_history: list[dict[str, Any]]
    security: dict[str, Any]
    metrics: dict[str, Any]
    users: list[dict[str, Any]]
    all_users: list[dict[str, Any]]
    groups: dict[str, Any]
    current_user: dict[str, Any]
    sudoers: str
