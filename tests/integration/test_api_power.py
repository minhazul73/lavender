import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_get_power_state_and_legacy_alias(auth_client):
    res1 = await auth_client.get("/api/power/state")
    assert res1.status_code == 200
    assert "active_governor" in res1.json()

    res2 = await auth_client.get("/api/device/power/state")
    assert res2.status_code == 200
    assert "active_governor" in res2.json()


@pytest.mark.asyncio
async def test_power_reboot_admin_gate(auth_client, admin_client):
    res_forbidden = await auth_client.post("/api/power/reboot")
    assert res_forbidden.status_code == 403

    with patch("server.api.power.run_sudo_async", return_value=(0, "Rebooting", "")):
        res_ok = await admin_client.post("/api/power/reboot")
        assert res_ok.status_code == 200
        assert res_ok.json()["action"] == "reboot"


@pytest.mark.asyncio
async def test_power_schedule_validation_and_admin_gate(auth_client, admin_client):
    # Forbidden for unprivileged
    res_forbidden = await auth_client.post("/api/power/schedule", json={"action": "reboot", "minutes": 10})
    assert res_forbidden.status_code == 403

    # Invalid action
    res_invalid_action = await admin_client.post("/api/power/schedule", json={"action": "invalid_action", "minutes": 10})
    assert res_invalid_action.status_code == 400

    # Invalid minutes
    res_invalid_minutes = await admin_client.post("/api/power/schedule", json={"action": "reboot", "minutes": 0})
    assert res_invalid_minutes.status_code == 400

    with patch("server.api.power.schedule_power_action", return_value={"success": True, "action": "reboot"}):
        res_ok = await admin_client.post("/api/power/schedule", json={"action": "reboot", "minutes": 15})
        assert res_ok.status_code == 200
        assert res_ok.json()["success"] is True
