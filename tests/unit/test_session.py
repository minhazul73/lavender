import time
import pytest
from server.auth.session import SessionStore, UserSession


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
