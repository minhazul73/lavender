"""Tests for dashboard.auth.deps: get_current_session and require_admin."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, status

from dashboard.auth.deps import get_current_session, require_admin, require_session
from dashboard.auth.session import UserSession


class _State:
    def __init__(self):
        self.session = None


class _Client:
    def __init__(self, host):
        self.host = host


class _Url:
    def __init__(self, path):
        self.path = path
        self.query = ""


class _Request:
    def __init__(
        self, cookies=None, headers=None, client_host="127.0.0.1", path="/api/test"
    ):
        self.cookies = cookies or {}
        self.headers = headers or {}
        self.client = _Client(client_host)
        self.state = _State()
        self.url = _Url(path)


def _make_request(
    cookies=None, headers=None, client_host="127.0.0.1", path="/api/test"
):
    return _Request(
        cookies=cookies, headers=headers, client_host=client_host, path=path
    )


class TestGetCurrentSession:
    def test_returns_none_when_no_cookie(self):
        request = _make_request()
        result = asyncio.run(get_current_session(request))
        assert result is None
        assert request.state.session is None

    def test_returns_session_from_valid_token(self):
        with patch("dashboard.auth.deps.session_store") as mock_store:
            session = UserSession(
                session_id="sid1",
                username="rahat",
                uid=1000,
                gid=1000,
                home="/home/rahat",
                shell="/bin/bash",
            )
            mock_store.verify_token.return_value = "sid1"
            mock_store._sessions = {"sid1": session}

            async def fake_get(sid):
                return session

            mock_store.get = fake_get
            request = _make_request(cookies={"rn7_session": "token"})
            result = asyncio.run(get_current_session(request))
        assert result is session

    def test_fallback_to_raw_token_when_verify_fails(self):
        with patch("dashboard.auth.deps.session_store") as mock_store:
            session = UserSession(
                session_id="rawtoken",
                username="rahat",
                uid=1000,
                gid=1000,
                home="/home/rahat",
                shell="/bin/bash",
            )
            mock_store.verify_token.return_value = None
            mock_store._sessions = {"rawtoken": session}

            async def fake_get(sid):
                return session

            mock_store.get = fake_get
            request = _make_request(cookies={"rn7_session": "rawtoken"})
            result = asyncio.run(get_current_session(request))
        assert result is session

    def test_localhost_dev_session_fallback(self):
        with patch("dashboard.auth.deps.session_store") as mock_store:
            session = UserSession(
                session_id="dev-session-active",
                username="dev",
                uid=1000,
                gid=1000,
                home="/home/dev",
                shell="/bin/bash",
            )
            mock_store.verify_token.return_value = None
            mock_store._sessions = {"dev-session-active": session}

            async def fake_get(sid):
                return session

            mock_store.get = fake_get
            request = _make_request(client_host="127.0.0.1")
            result = asyncio.run(get_current_session(request))
        assert result is session

    def test_no_fallback_for_remote_client(self):
        with patch("dashboard.auth.deps.session_store") as mock_store:
            mock_store.verify_token.return_value = None
            mock_store._sessions = {"dev-session-active": "x"}
            request = _make_request(client_host="203.0.113.5")
            result = asyncio.run(get_current_session(request))
        assert result is None

    def test_already_resolved_session_in_state(self):
        request = _make_request()
        existing = UserSession(
            session_id="cached",
            username="rahat",
            uid=1000,
            gid=1000,
            home="/home/rahat",
            shell="/bin/bash",
        )
        request.state.session = existing
        result = asyncio.run(get_current_session(request))
        assert result is existing


class TestRequireSession:
    def test_returns_session_when_present(self):
        request = _make_request()
        session = UserSession(
            session_id="x",
            username="rahat",
            uid=1000,
            gid=1000,
            home="/home/rahat",
            shell="/bin/bash",
        )
        result = asyncio.run(require_session(request, session))
        assert result is session

    def test_redirects_html_when_no_session(self):
        request = _make_request(headers={"accept": "text/html"}, path="/dashboard")
        with pytest.raises(HTTPException) as exc:
            asyncio.run(require_session(request, None))
        assert exc.value.status_code == status.HTTP_307_TEMPORARY_REDIRECT
        assert "/login" in exc.value.headers["Location"]

    def test_401_for_api_when_no_session(self):
        request = _make_request(headers={"accept": "application/json"}, path="/api/x")
        with pytest.raises(HTTPException) as exc:
            asyncio.run(require_session(request, None))
        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestRequireAdmin:
    def _session(self, elevated=False):
        session = MagicMock()
        session.is_elevated.return_value = elevated
        session.elevate = MagicMock()
        return session

    def test_returns_session_when_elevated(self):
        request = _make_request()
        session = self._session(elevated=True)
        result = asyncio.run(require_admin(request, session))
        assert result is session

    def test_elevates_with_valid_password(self):
        request = _make_request(headers={"X-Admin-Password": "secret"})
        session = self._session(elevated=False)
        with patch(
            "dashboard.auth.bridge.verify_sudo_password", return_value=(True, "")
        ):
            result = asyncio.run(require_admin(request, session))
        assert result is session
        session.elevate.assert_called_once()

    def test_rejects_with_invalid_password(self):
        request = _make_request(headers={"X-Admin-Password": "wrong"})
        session = self._session(elevated=False)
        with patch(
            "dashboard.auth.bridge.verify_sudo_password", return_value=(False, "bad")
        ):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(require_admin(request, session))
        assert exc.value.status_code == status.HTTP_403_FORBIDDEN

    def test_rejects_when_no_password_and_not_elevated(self):
        request = _make_request()
        session = self._session(elevated=False)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(require_admin(request, session))
        assert exc.value.status_code == status.HTTP_403_FORBIDDEN
