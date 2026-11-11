import time

import pytest

from server.auth.session import SessionStore


@pytest.mark.asyncio
async def test_session_lifecycle():
    store = SessionStore()
    user_info = {
        "uid": 1000,
        "gid": 1000,
        "home": "/home/alice",
        "shell": "/bin/bash",
        "groups": ["alice", "wheel"],
    }
    session = await store.create("alice", user_info)
    assert session.username == "alice"
    assert session.uid == 1000
    assert session.can_elevate()
    assert not session.is_elevated()

    # Sign token
    token = store.sign_session_id(session.session_id)
    assert token is not None
    verified_sid = store.verify_token(token)
    assert verified_sid == session.session_id

    # Retrieve session
    fetched = await store.get(session.session_id)
    assert fetched is not None
    assert fetched.username == "alice"

    # Elevation
    session.elevate(timeout_minutes=15)
    assert session.is_elevated()
    assert session.admin_remaining_seconds() > 0

    session.drop_elevation()
    assert not session.is_elevated()

    # Deletion
    await store.delete(session.session_id)
    assert await store.get(session.session_id) is None


@pytest.mark.asyncio
async def test_session_idle_cleanup():
    store = SessionStore()
    user_info = {"uid": 1001, "gid": 1001, "home": "/home/bob", "shell": "/bin/sh", "groups": []}
    session = await store.create("bob", user_info)

    # Artificially age the session past 60 minutes
    session.last_used = time.time() - 3700

    # Getting aged session should trigger expiration
    fetched = await store.get(session.session_id)
    assert fetched is None


@pytest.mark.asyncio
async def test_session_cleanup_idle_removes_expired_and_releases_lock():
    """Verify cleanup_idle removes expired sessions and releases lock before logging."""
    store = SessionStore()
    user_info = {"uid": 1002, "gid": 1002, "home": "/home/charlie", "shell": "/bin/sh", "groups": []}
    session = await store.create("charlie", user_info)
    session.last_used = time.time() - 4000

    await store.cleanup_idle()
    assert session.session_id not in store._sessions
    assert not store._lock.locked()


@pytest.mark.asyncio
async def test_session_store_max_sessions_eviction(monkeypatch):
    import server.auth.session as session_mod
    monkeypatch.setattr(session_mod, "MAX_SESSIONS", 3)

    store = SessionStore()
    u1 = await store.create("user1", {"uid": 1001, "gid": 1001})
    u1.last_used = time.time() - 100
    u2 = await store.create("user2", {"uid": 1002, "gid": 1002})
    u2.last_used = time.time() - 50
    u3 = await store.create("user3", {"uid": 1003, "gid": 1003})
    u3.last_used = time.time() - 10

    assert len(store._sessions) == 3

    # Adding 4th session when at max capacity should evict oldest (u1)
    u4 = await store.create("user4", {"uid": 1004, "gid": 1004})
    assert len(store._sessions) == 3
    assert u1.session_id not in store._sessions
    assert u2.session_id in store._sessions
    assert u3.session_id in store._sessions
    assert u4.session_id in store._sessions

    # If an idle/expired session exists, it should be evicted first
    u2.last_used = time.time() - 4000  # expired
    u5 = await store.create("user5", {"uid": 1005, "gid": 1005})
    assert len(store._sessions) == 3
    assert u2.session_id not in store._sessions
    assert u3.session_id in store._sessions
    assert u4.session_id in store._sessions
    assert u5.session_id in store._sessions

