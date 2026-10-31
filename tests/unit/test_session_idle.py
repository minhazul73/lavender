"""Tests for SessionStore idle timeout and cleanup behavior."""

import asyncio
import time

from dashboard.auth.session import SessionStore, UserSession
from dashboard.config import SESSION_MAX_IDLE_MINUTES


def _make_session(store, username="rahat", uid=1000, **kwargs):
    user_info = {
        "uid": uid,
        "gid": uid,
        "home": f"/home/{username}",
        "shell": "/bin/bash",
        "groups": ["wheel"],
    }
    user_info.update(kwargs)
    return asyncio.run(store.create(username, user_info))


class TestSessionIdleTimeout:
    def test_get_returns_session_within_idle_window(self):
        store = SessionStore()
        session = _make_session(store)
        fetched = asyncio.run(store.get(session.session_id))
        assert fetched is session
        assert fetched.last_used >= session.last_used  # touched

    def test_get_returns_none_after_idle_timeout(self):
        store = SessionStore()
        session = _make_session(store)
        # Backdate last_used so it exceeds the idle window
        session.last_used = time.time() - (SESSION_MAX_IDLE_MINUTES * 60 + 60)
        fetched = asyncio.run(store.get(session.session_id))
        assert fetched is None
        assert session.session_id not in store._sessions

    def test_cleanup_idle_removes_expired_sessions(self):
        store = SessionStore()
        fresh = _make_session(store, username="fresh")
        stale = _make_session(store, username="stale")
        stale.last_used = time.time() - (SESSION_MAX_IDLE_MINUTES * 60 + 120)
        asyncio.run(store.cleanup_idle())
        assert fresh.session_id in store._sessions
        assert stale.session_id not in store._sessions

    def test_cleanup_idle_keeps_all_when_none_expired(self):
        store = SessionStore()
        _make_session(store, username="a")
        _make_session(store, username="b")
        asyncio.run(store.cleanup_idle())
        assert len(store._sessions) == 2

    def test_delete_removes_session(self):
        store = SessionStore()
        session = _make_session(store)
        asyncio.run(store.delete(session.session_id))
        assert session.session_id not in store._sessions

    def test_delete_missing_session_is_noop(self):
        store = SessionStore()
        asyncio.run(store.delete("nonexistent"))
        # Should not raise

    def test_touch_updates_last_used(self):
        store = SessionStore()
        session = _make_session(store)
        original = session.last_used
        time.sleep(0.01)
        session.touch()
        assert session.last_used > original

    def test_admin_remaining_seconds_with_elevation(self):
        session = UserSession(
            session_id="x",
            username="rahat",
            uid=1000,
            gid=1000,
            home="/home/rahat",
            shell="/bin/bash",
            is_admin=True,
            admin_until=time.time() + 120,
        )
        remaining = session.admin_remaining_seconds()
        assert 110 <= remaining <= 120

    def test_admin_remaining_seconds_no_admin(self):
        session = UserSession(
            session_id="x",
            username="rahat",
            uid=1000,
            gid=1000,
            home="/home/rahat",
            shell="/bin/bash",
        )
        assert session.admin_remaining_seconds() == 0

    def test_elevate_sets_admin_until(self):
        session = UserSession(
            session_id="x",
            username="rahat",
            uid=1000,
            gid=1000,
            home="/home/rahat",
            shell="/bin/bash",
        )
        before = time.time()
        session.elevate(timeout_minutes=5)
        assert session.is_admin is True
        assert session.admin_until is not None
        assert session.admin_until >= before + 290  # 5 min minus slop

    def test_drop_elevation_clears_admin(self):
        session = UserSession(
            session_id="x",
            username="rahat",
            uid=1000,
            gid=1000,
            home="/home/rahat",
            shell="/bin/bash",
            is_admin=True,
            admin_until=time.time() + 100,
        )
        session.drop_elevation()
        assert session.is_admin is False
        assert session.admin_until is None

    def test_token_round_trip(self):
        store = SessionStore()
        token = store.sign_session_id("abc123")
        assert store.verify_token(token) == "abc123"

    def test_token_tampered_returns_none(self):
        store = SessionStore()
        token = store.sign_session_id("abc123")
        assert store.verify_token(token + "x") is None
