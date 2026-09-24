from typing import Optional, List
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, description="Linux username")
    password: str = Field(..., min_length=1, description="Linux password")
    next: Optional[str] = Field(default="/", description="Redirect path after login")


class ElevateRequest(BaseModel):
    password: str = Field(..., min_length=1, description="Sudo password for administrative elevation")


class LoginResponse(BaseModel):
    success: bool
    username: str
    redirect: str
    is_admin: bool
    can_elevate: bool


class ElevationResponse(BaseModel):
    success: bool
    is_admin: bool
    expires_in: int


class UserProfileResponse(BaseModel):
    username: str
    uid: int
    gid: int
    home: str
    shell: str
    groups: List[str]
    is_admin: bool
    can_elevate: bool
    admin_remaining_seconds: int
    connected: bool = True
