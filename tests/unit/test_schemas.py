import pytest
from pydantic import ValidationError
from server.schemas.auth import LoginRequest, ElevateRequest, LoginResponse
from server.schemas.power import SchedulePowerRequest
from server.schemas.users import TerminateSessionRequest, AddSshKeyRequest


def test_login_request_validation():
    req = LoginRequest(username="admin", password="password123", next="/services")
    assert req.username == "admin"
    assert req.next == "/services"

    with pytest.raises(ValidationError):
        LoginRequest(username="", password="pwd")


def test_schedule_power_validation():
    valid = SchedulePowerRequest(action="reboot", minutes=30)
    assert valid.action == "reboot"
    assert valid.minutes == 30

    with pytest.raises(ValidationError):
        SchedulePowerRequest(action="reboot", minutes=0)  # ge=1

    with pytest.raises(ValidationError):
        SchedulePowerRequest(action="reboot", minutes=2000)  # le=1440


def test_ssh_key_request_validation():
    valid = AddSshKeyRequest(key="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIG mock@test")
    assert "ssh-ed25519" in valid.key

    with pytest.raises(ValidationError):
        AddSshKeyRequest(key="too_short")
