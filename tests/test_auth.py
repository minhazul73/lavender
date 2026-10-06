"""
Unit tests for authentication module.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from dashboard.auth.session import UserSession, SessionStore
from dashboard.auth.bridge import verify_linux_credentials, AuthError
from dashboard.auth.deps import get_current_session, require_session


class TestUserSession:
    """Test UserSession dataclass and methods."""

    def test_is_elevated_root(self):
        """Test elevation check for root user."""
        session = UserSession(
            session_id="test",
            username="root",
            uid=0,
            gid=0,
            home="/root",
            shell="/bin/bash",
            is_admin=True,
        )
        assert session.is_elevated() is True

    def test_is_elevated_admin_groups(self):
        """Test elevation check for admin group members."""
        session = UserSession(
            session_id="test",
            username="admin",
            uid=1000,
            gid=1000,
            home="/home/admin",
            shell="/bin/bash",
            groups=["wheel", "sudo"],
            is_admin=True,
        )
        assert session.is_elevated() is True

    def test_is_elevated_timeout(self):
        """Test elevation timeout."""
        import time
        session = UserSession(
            session_id="test",
            username="user",
            uid=1000,
            gid=1000,
            home="/home/user",
            shell="/bin/bash",
            is_admin=True,
            admin_until=time.time() - 100,  # Expired
        )
        assert session.is_elevated() is False

    def test_can_elevate(self):
        """Test can_elevate checks groups."""
        session = UserSession(
            session_id="test",
            username="user",
            uid=1000,
            gid=1000,
            home="/home/user",
            shell="/bin/bash",
            groups=["wheel", "audio"],
        )
        assert session.can_elevate() is True

    def test_to_dict(self):
        """Test session serialization."""
        session = UserSession(
            session_id="abc123",
            username="testuser",
            uid=1000,
            gid=1000,
            home="/home/testuser",
            shell="/bin/bash",
            groups=["wheel"],
            is_admin=True,
        )
        data = session.to_dict()
        assert data["username"] == "testuser"
        assert data["uid"] == 1000
        assert data["is_admin"] is True
        assert data["can_elevate"] is True


class TestSessionStore:
    """Test SessionStore functionality."""

    def test_create_session(self):
        """Test session creation."""
        store = SessionStore()
        user_info = {
            "uid": 1000,
            "gid": 1000,
            "home": "/home/test",
            "shell": "/bin/bash",
            "groups": ["wheel"],
        }
        # Note: create is async
        import asyncio
        session = asyncio.run(store.create("testuser", user_info))
        assert session.username == "testuser"
        assert session.session_id is not None

    def test_verify_token(self):
        """Test token signing and verification."""
        store = SessionStore()
        token = store.sign_session_id("test-session-id")
        assert token is not None
        sid = store.verify_token(token)
        assert sid == "test-session-id"

    def test_verify_invalid_token(self):
        """Test invalid token returns None."""
        store = SessionStore()
        sid = store.verify_token("invalid-token")
        assert sid is None


class TestAuthBridge:
    """Test authentication bridge functions."""

    @patch("dashboard.auth.bridge.subprocess.run")
    def test_verify_sudo_password_success(self, mock_run):
        """Test sudo password verification success."""
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        with patch.dict("sys.modules", {"spwd": None, "pam": None}):
            assert verify_linux_credentials("user", "secret") is True
        assert mock_run.called

    def test_auth_error_exception(self):
        """Test AuthError can be raised."""
        with pytest.raises(AuthError):
            raise AuthError("Test error")


class TestAuthDeps:
    """Test authentication dependencies."""

    def test_require_session_no_session_api(self):
        """Test require_session raises 401 for API calls without a session."""
        import asyncio
        from fastapi import HTTPException
        request = MagicMock()
        request.headers = {"accept": "application/json"}
        request.url.path = "/api/x"
        request.url.query = ""
        with pytest.raises(HTTPException) as exc:
            asyncio.run(require_session(request, None))
        assert exc.value.status_code == 401

    def test_require_session_with_session(self):
        """Test require_session returns the existing session."""
        import asyncio
        session = MagicMock()
        assert asyncio.run(require_session(MagicMock(), session)) is session