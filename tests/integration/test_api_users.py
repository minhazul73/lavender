import pytest
from unittest.mock import patch
from server.core.executor import CommandResult


@pytest.mark.asyncio
async def test_get_users_and_legacy_alias(auth_client):
    res1 = await auth_client.get("/api/users")
    assert res1.status_code == 200
    data1 = res1.json()
    assert "human_users" in data1
    assert "metrics" in data1

    res2 = await auth_client.get("/api/device/users")
    assert res2.status_code == 200
    data2 = res2.json()
    assert "human_users" in data2
    assert "metrics" in data2


@pytest.mark.asyncio
async def test_ssh_keys_crud(auth_client, regular_session):
    with patch("server.api.users.get_user_ssh_keys", return_value=["ssh-ed25519 AAAAC3Nza mock@key"]):
        res1 = await auth_client.get(f"/api/users/{regular_session.username}/ssh-keys")
        assert res1.status_code == 200
        assert len(res1.json()["keys"]) == 1

        res2 = await auth_client.get(f"/api/device/users/{regular_session.username}/ssh-keys")
        assert res2.status_code == 200
        assert len(res2.json()["keys"]) == 1


@pytest.mark.asyncio
async def test_session_terminate_admin_gate(auth_client, admin_client):
    res_forbidden = await auth_client.post("/api/users/session/terminate", json={"tty": "pts/2"})
    assert res_forbidden.status_code == 403

    with patch("server.api.users.run_sudo_async", return_value=(0, "", "")):
        res_ok = await admin_client.post("/api/users/session/terminate", json={"tty": "pts/2"})
        assert res_ok.status_code == 200
        assert res_ok.json()["success"] is True


@pytest.mark.asyncio
async def test_change_password(auth_client, regular_session, mock_executor):
    mock_executor.set_default(CommandResult(0, "", ""))
    res = await auth_client.post(
        f"/api/users/{regular_session.username}/password",
        json={"new_password": "brand_new_secret_pwd"},
    )
    assert res.status_code == 200
    assert res.json()["success"] is True
