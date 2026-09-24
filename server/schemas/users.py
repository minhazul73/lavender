from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TerminateSessionRequest(BaseModel):
    tty: str = Field(..., min_length=1, description="TTY name to terminate")


class AddSshKeyRequest(BaseModel):
    key: str = Field(..., min_length=10, description="Public SSH key string")


class UpdateUserGroupsRequest(BaseModel):
    groups: List[str] = Field(..., description="Target list of secondary group names")


class ChangePasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=4, description="New user password")


class UsersOverviewResponse(BaseModel):
    human_users: List[Dict[str, Any]]
    system_users: List[Dict[str, Any]]
    groups_categorized: Dict[str, Any]
    active_sessions: List[Dict[str, Any]]
    login_history: List[Dict[str, Any]]
    security: Dict[str, Any]
    metrics: Dict[str, Any]
    users: List[Dict[str, Any]]
    all_users: List[Dict[str, Any]]
    groups: Dict[str, Any]
    current_user: Dict[str, Any]
    sudoers: str
