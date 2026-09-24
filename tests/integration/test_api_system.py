import pytest
from unittest.mock import patch
from server.core.executor import CommandResult


@pytest.mark.asyncio
async def test_get_system_services(auth_client, mock_executor):
    mock_executor.register_prefix(
        ["systemctl", "list-units"],
        CommandResult(0, "ssh.service loaded active running OpenSSH server\nnginx.service loaded active running Nginx", ""),
    )
    res = await auth_client.get("/api/system/services")
    assert res.status_code == 200
    data = res.json()
    assert "services" in data
    assert "count" in data


@pytest.mark.asyncio
async def test_get_system_storage(auth_client):
    res = await auth_client.get("/api/system/storage")
    assert res.status_code == 200
    data = res.json()
    assert "disks" in data


@pytest.mark.asyncio
async def test_get_system_processes(auth_client):
    res = await auth_client.get("/api/system/processes?limit=5")
    assert res.status_code == 200
    data = res.json()
    assert "processes" in data
    assert "load" in data
    assert "memory" in data


@pytest.mark.asyncio
async def test_kill_process_admin_gate(auth_client, admin_client, mock_executor):
    # Regular user should be rejected with 403
    res_forbidden = await auth_client.post("/api/system/processes/kill?pid=99999")
    assert res_forbidden.status_code == 403

    # Admin user permitted
    mock_executor.register(["sudo", "kill", "-9", "99999"], CommandResult(0, "", ""))
    with patch("server.api.system.run_sudo_async", return_value=(0, "Killed", "")):
        res_admin = await admin_client.post("/api/system/processes/kill?pid=99999")
        assert res_admin.status_code == 200
        assert res_admin.json()["success"] is True
