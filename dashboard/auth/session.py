"""
In-memory session management for authenticated Linux users (Native Linux PAM).
"""
import time
import secrets
import logging
from dataclasses import dataclass, field
from typing import Optional
from itsdangerous import URLSafeSerializer, BadSignature, SignatureExpired

from dashboard.config import (
    SESSION_SECRET_KEY,
    SESSION_MAX_IDLE_MINUTES,
    ADMIN_ELEVATION_TIMEOUT_MINUTES,
)

logger = logging.getLogger(__name__)


@dataclass
class UserSession:
    session_id: str
    username: str
    uid: int
    gid: int
    home: str
    shell: str
    groups: list[str] = field(default_factory=list)
    is_admin: bool = False
    admin_until: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)

    def is_elevated(self) -> bool:
        """Check if administrative access is currently active and unexpired."""
        if not self.is_admin:
            return False
        if self.admin_until is None:
            return True
        if time.time() > self.admin_until:
            self.is_admin = False
            self.admin_until = None
            return False
        return True

    def admin_remaining_seconds(self) -> int:
        """Remaining seconds for administrative elevation."""
        if not self.is_admin:
            return 0
        if self.admin_until is None:
            return 9999
        rem = int(self.admin_until - time.time())
        return max(0, rem)

    def elevate(self, timeout_minutes: int = ADMIN_ELEVATION_TIMEOUT_MINUTES) -> None:
        """Elevate to admin status with a timeout ticket."""
        self.is_admin = True
        self.admin_until = time.time() + (timeout_minutes * 60)

    def drop_elevation(self) -> None:
        """Revoke administrative privileges."""
        self.is_admin = False
        self.admin_until = None

    def can_elevate(self) -> bool:
        """Check if user belongs to wheel/sudo/root groups or has uid 0."""
        admin_groups = {"wheel", "sudo", "root"}
        return self.uid == 0 or bool(admin_groups.intersection(set(self.groups)))

    def touch(self) -> None:
        """Update last used timestamp to prevent idle timeout."""
        self.last_used = time.time()

    def to_dict(self) -> dict:
        """Serialize safe session state for JSON responses."""
        return {
            "username": self.username,
            "uid": self.uid,
            "gid": self.gid,
            "home": self.home,
            "shell": self.shell,
            "groups": self.groups,
            "is_admin": self.is_elevated(),
            "can_elevate": self.can_elevate(),
            "admin_remaining_seconds": self.admin_remaining_seconds(),
            "connected": True,
        }


class SessionStore:
    """Thread-safe in-memory session repository with signed cookie tokens."""

    def __init__(self):
        self._sessions: dict[str, UserSession] = {}
        self._serializer = URLSafeSerializer(SESSION_SECRET_KEY, salt="dashboard-session-salt")

    def sign_session_id(self, session_id: str) -> str:
        """Sign session ID into a cryptographically secured token for cookie storage."""
        return self._serializer.dumps({"sid": session_id})

    def verify_token(self, token: str) -> Optional[str]:
        """Verify signed cookie token and return the raw session_id."""
        try:
            data = self._serializer.loads(token)
            return data.get("sid")
        except (BadSignature, SignatureExpired, Exception):
            return None

    async def create(
        self,
        username: str,
        user_info: dict,
    ) -> UserSession:
        """Create and store a new user session."""
        sid = secrets.token_hex(32)
        session = UserSession(
            session_id=sid,
            username=username,
            uid=user_info.get("uid", 1000),
            gid=user_info.get("gid", 1000),
            home=user_info.get("home", f"/home/{username}"),
            shell=user_info.get("shell", "/bin/sh"),
            groups=user_info.get("groups", []),
            is_admin=False,
        )
        self._sessions[sid] = session
        logger.info(
            "Created session %s for user %s (uid=%d)",
            sid[:8], username, session.uid
        )
        return session

    async def get(self, session_id: str) -> Optional[UserSession]:
        """Retrieve active session, verifying idle timeout."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        # Check idle expiration
        max_idle_seconds = SESSION_MAX_IDLE_MINUTES * 60
        if time.time() - session.last_used > max_idle_seconds:
            logger.info("Session %s for %s timed out due to inactivity", session_id[:8], session.username)
            await self.delete(session_id)
            return None

        session.touch()
        return session

    async def delete(self, session_id: str) -> None:
        """Delete session from memory."""
        session = self._sessions.pop(session_id, None)
        if session:
            logger.info("Terminated session %s for user %s", session_id[:8], session.username)

    async def cleanup_idle(self) -> None:
        """Periodic cleaner for expired idle sessions."""
        now = time.time()
        max_idle_seconds = SESSION_MAX_IDLE_MINUTES * 60
        expired_ids = [
            sid for sid, s in list(self._sessions.items())
            if (now - s.last_used > max_idle_seconds)
        ]
        for sid in expired_ids:
            await self.delete(sid)


# Global session repository instance
session_store = SessionStore()
