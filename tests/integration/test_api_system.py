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


@pytest.mark.asyncio
async def test_get_system_logs(auth_client):
    res = await auth_client.get("/api/system/logs?limit=5")
    assert res.status_code == 200
    data = res.json()
    assert "logs" in data
    assert "count" in data
    assert isinstance(data["logs"], list)
    if data["logs"]:
        first = data["logs"][0]
        assert "timestamp" in first
        assert "message" in first
        assert "service" in first
        assert "level" in first


@pytest.mark.asyncio
async def test_service_action_rejects_flag_injection(auth_client):
    res = await auth_client.post("/api/services/--version/restart")
    assert res.status_code == 400
    assert "Invalid service name" in res.json()["detail"]


@pytest.mark.asyncio
async def test_service_action_rejects_metacharacters(auth_client):
    res = await auth_client.post("/api/services/nginx;rm/restart")
    assert res.status_code == 400
    assert "Invalid service name" in res.json()["detail"]


@pytest.mark.asyncio
async def test_service_logs_rejects_invalid_service_name(auth_client):
    res = await auth_client.get("/api/services/--all/logs")
    assert res.status_code == 400
    assert "Invalid service name" in res.json()["detail"]


def test_validate_service_name_unit():
    from fastapi import HTTPException
    from server.api.system import validate_service_name

    # Valid service names
    assert validate_service_name("nginx") == "nginx"
    assert validate_service_name("nginx.service") == "nginx.service"
    assert validate_service_name("getty@tty1") == "getty@tty1"
    assert validate_service_name("systemd-resolved") == "systemd-resolved"
    assert validate_service_name("user@1000.service") == "user@1000.service"

    # Invalid service names
    for bad in ["--version", "-H", "nginx;rm", "nginx|sh", "nginx rm", "", "a" * 257]:
        with pytest.raises(HTTPException) as exc_info:
            validate_service_name(bad)
        assert exc_info.value.status_code == 400
        assert "Invalid service name" in exc_info.value.detail


