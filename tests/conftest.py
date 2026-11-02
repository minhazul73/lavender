import asyncio
import os
import pytest
from httpx import AsyncClient, ASGITransport

from server.core.config import SESSION_COOKIE_NAME
from server.core.executor import (
    CommandResult,
    SystemCommandExecutor,
    get_executor,
    set_executor,
)
from server.core.sysfs import (
    SystemSysfsReader,
    get_sysfs_reader,
    set_sysfs_reader,
)
from server.auth.session import UserSession, session_store
from server.main import app
from tests.mocks.executor import MockCommandExecutor
from tests.mocks.sysfs import MockSysfsReader


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "mocks", "fixtures")


@pytest.fixture
def mock_executor():
    """Fixture providing a configurable mock command executor and resetting afterwards."""
    executor = MockCommandExecutor()
    set_executor(executor)
    yield executor
    set_executor(SystemCommandExecutor())


@pytest.fixture
def mock_sysfs():
    """Fixture providing an in-memory sysfs/procfs reader preloaded with baseline fake stats."""
    proc_stat = ""
    proc_meminfo = ""
    proc_stat_path = os.path.join(FIXTURES_DIR, "proc_stat.txt")
    proc_meminfo_path = os.path.join(FIXTURES_DIR, "proc_meminfo.txt")

    if os.path.isfile(proc_stat_path):
        with open(proc_stat_path, "r") as f:
            proc_stat = f.read()
    if os.path.isfile(proc_meminfo_path):
        with open(proc_meminfo_path, "r") as f:
            proc_meminfo = f.read()

    reader = MockSysfsReader({
        "/proc/stat": proc_stat,
        "/proc/meminfo": proc_meminfo,
        "/proc/loadavg": "0.15 0.20 0.18 1/150 12345",
        "/proc/uptime": "123456.78 456789.01",
        "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq": "1800000",
        "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor": "schedutil",
        "/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors": "performance powersave schedutil",
    })
    set_sysfs_reader(reader)
    yield reader
    set_sysfs_reader(SystemSysfsReader())


@pytest.fixture
async def regular_session():
    """Fixture creating an active regular user session."""
    sid = "test-regular-session-id"
    session = UserSession(
        session_id=sid,
        username="testuser",
        uid=1000,
        gid=1000,
        home="/home/testuser",
        shell="/bin/bash",
        groups=["testuser"],
        is_admin=False,
    )
    session_store._sessions[sid] = session
    yield session
    session_store._sessions.pop(sid, None)


@pytest.fixture
async def admin_session():
    """Fixture creating an active elevated administrative session."""
    sid = "test-admin-session-id"
    session = UserSession(
        session_id=sid,
        username="adminuser",
        uid=1000,
        gid=1000,
        home="/home/adminuser",
        shell="/bin/bash",
        groups=["adminuser", "wheel", "sudo"],
        is_admin=True,
    )
    session.elevate(timeout_minutes=60)
    session_store._sessions[sid] = session
    yield session
    session_store._sessions.pop(sid, None)


@pytest.fixture
async def client():
    """Public unauthenticated AsyncClient."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
async def auth_client(regular_session):
    """AsyncClient authenticated as regular user."""
    token = session_store.sign_session_id(regular_session.session_id)
    cookies = {SESSION_COOKIE_NAME: token}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", cookies=cookies) as ac:
        yield ac


@pytest.fixture
async def admin_client(admin_session):
    """AsyncClient authenticated as elevated administrator."""
    token = session_store.sign_session_id(admin_session.session_id)
    cookies = {SESSION_COOKIE_NAME: token}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", cookies=cookies) as ac:
        yield ac
