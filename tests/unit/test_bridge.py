import asyncio
from unittest.mock import patch
import pytest

from server.auth.bridge import run_command_async, run_sudo_async, run_user_service_async


@pytest.mark.asyncio
async def test_run_command_async_success():
    code, out, err = await run_command_async(["echo", "hello"])
    assert code == 0
    assert out == "hello"


@pytest.mark.asyncio
async def test_run_command_async_timeout():
    code, out, err = await run_command_async(["sleep", "2"], timeout=0.1)
    assert code == -1
    assert "timed out" in err.lower()


@pytest.mark.asyncio
async def test_run_sudo_async_timeout_handling():
    with patch("server.auth.bridge.asyncio.wait_for", side_effect=asyncio.TimeoutError):
        code, out, err = await run_sudo_async(["apt-get", "upgrade"], password=None, timeout=1)
        assert code == -1
        assert "timed out" in err.lower()


@pytest.mark.asyncio
async def test_run_user_service_async_timeout_handling():
    with patch("server.auth.bridge.asyncio.wait_for", side_effect=asyncio.TimeoutError):
        code, out, err = await run_user_service_async(1000, ["systemctl", "--user", "status"], timeout=1)
        assert code == -1
        assert "timed out" in err.lower()


def test_auth_bridge_handles_missing_spwd(monkeypatch):
    import subprocess
    import sys
    from unittest.mock import MagicMock
    from server.auth.bridge import verify_linux_credentials

    monkeypatch.setitem(sys.modules, "spwd", None)
    monkeypatch.setitem(sys.modules, "crypt", None)

    mock_pam_mod = MagicMock()
    mock_pam_instance = MagicMock()
    mock_pam_mod.pam.return_value = mock_pam_instance
    monkeypatch.setitem(sys.modules, "pam", mock_pam_mod)

    # Case 1: PAM succeeds after spwd missing
    mock_pam_instance.authenticate.return_value = True
    assert verify_linux_credentials("testuser", "testpassword") is True

    # Case 2: PAM fails, sudo succeeds
    mock_pam_instance.authenticate.return_value = False
    with patch("subprocess.run") as mock_subproc:
        mock_subproc.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        assert verify_linux_credentials("testuser", "testpassword") is True

    # Case 3: Both PAM and sudo fail
    with patch("subprocess.run") as mock_subproc:
        mock_subproc.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error")
        assert verify_linux_credentials("testuser", "wrongpassword") is False


