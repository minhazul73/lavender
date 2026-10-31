"""
Unit tests for dashboard.services.power — failure and edge-case scenarios.
"""

import pytest
from unittest.mock import patch

from dashboard.services import power


class TestPoweroff:
    @patch("dashboard.services.power.run_sudo_command")
    def test_poweroff_success(self, mock_sudo):
        mock_sudo.return_value = (0, "Power off initiated", "")
        res = power.poweroff()
        assert res["action"] == "poweroff"
        assert res["success"] is True
        assert res["output"] == "Power off initiated"
        assert res["error"] == ""

    @patch("dashboard.services.power.run_sudo_command")
    def test_poweroff_failure(self, mock_sudo):
        mock_sudo.return_value = (1, "", "Interactive authentication required")
        res = power.poweroff()
        assert res["success"] is False
        assert res["error"] == "Interactive authentication required"

    @patch("dashboard.services.power.run_sudo_command")
    def test_poweroff_exception(self, mock_sudo):
        """poweroff() does not catch exceptions — they propagate."""
        mock_sudo.side_effect = OSError("spawn failed")
        with pytest.raises(OSError, match="spawn failed"):
            power.poweroff()


class TestSuspend:
    @patch("dashboard.services.power.run_sudo_command")
    def test_suspend_success(self, mock_sudo):
        mock_sudo.return_value = (0, "Suspended", "")
        res = power.suspend()
        assert res["action"] == "suspend"
        assert res["success"] is True

    @patch("dashboard.services.power.run_sudo_command")
    def test_suspend_failure(self, mock_sudo):
        mock_sudo.return_value = (1, "", "Suspend failed")
        res = power.suspend()
        assert res["success"] is False
        assert res["error"] == "Suspend failed"


class TestSchedulePowerAction:
    @patch("dashboard.services.power.run_sudo_command")
    def test_schedule_reboot_success(self, mock_sudo):
        mock_sudo.return_value = (0, "Scheduled reboot", "")
        res = power.schedule_power_action("reboot", 5, "Message")
        assert res["success"] is True
        assert res["action"] == "reboot"
        assert res["minutes"] == 5
        cmd = mock_sudo.call_args[0][0]
        assert cmd[:3] == ["shutdown", "-r", "+5"]
        assert "Message" in cmd

    @patch("dashboard.services.power.run_sudo_command")
    def test_schedule_poweroff_success(self, mock_sudo):
        mock_sudo.return_value = (0, "Scheduled poweroff", "")
        res = power.schedule_power_action("poweroff", 10)
        assert res["success"] is True
        assert res["action"] == "poweroff"
        cmd = mock_sudo.call_args[0][0]
        assert cmd[:3] == ["shutdown", "-h", "+10"]

    @patch("dashboard.services.power.run_sudo_command")
    def test_schedule_no_message(self, mock_sudo):
        mock_sudo.return_value = (0, "", "")
        res = power.schedule_power_action("reboot", 5)
        assert res["success"] is True
        cmd = mock_sudo.call_args[0][0]
        assert cmd == ["shutdown", "-r", "+5"]

    @patch("dashboard.services.power.run_sudo_command")
    def test_schedule_failure(self, mock_sudo):
        mock_sudo.return_value = (1, "", "Permission denied")
        res = power.schedule_power_action("reboot", 5)
        assert res["success"] is False
        assert res["error"] == "Permission denied"

    @patch("dashboard.services.power.run_sudo_command")
    def test_schedule_exception(self, mock_sudo):
        """schedule_power_action() does not catch exceptions — they propagate."""
        mock_sudo.side_effect = OSError("spawn failed")
        with pytest.raises(OSError, match="spawn failed"):
            power.schedule_power_action("reboot", 5)


class TestCancelScheduledAction:
    @patch("dashboard.services.power.run_sudo_command")
    def test_cancel_success(self, mock_sudo):
        mock_sudo.return_value = (0, "Cancelled", "")
        res = power.cancel_scheduled_action()
        assert res["success"] is True
        cmd = mock_sudo.call_args[0][0]
        assert cmd == ["shutdown", "-c"]

    @patch("dashboard.services.power.run_sudo_command")
    def test_cancel_failure(self, mock_sudo):
        mock_sudo.return_value = (1, "", "No scheduled shutdown")
        res = power.cancel_scheduled_action()
        assert res["success"] is False
        assert res["error"] == "No scheduled shutdown"

    @patch("dashboard.services.power.run_sudo_command")
    def test_cancel_exception(self, mock_sudo):
        """cancel_scheduled_action() does not catch exceptions — they propagate."""
        mock_sudo.side_effect = OSError("spawn failed")
        with pytest.raises(OSError, match="spawn failed"):
            power.cancel_scheduled_action()


class TestGetScheduledShutdown:
    @patch("dashboard.services.power.run_command")
    def test_scheduled_shutdown_active(self, mock_cmd):
        mock_cmd.return_value = (0, "Shutdown scheduled for Mon Oct 31 12:00", "")
        res = power.get_scheduled_shutdown()
        assert res["scheduled"] is True
        assert "Shutdown scheduled" in res["details"]

    @patch("dashboard.services.power.run_command")
    def test_scheduled_shutdown_none(self, mock_cmd):
        mock_cmd.return_value = (1, "", "No scheduled shutdown")
        res = power.get_scheduled_shutdown()
        assert res["scheduled"] is False
        assert res["details"] is None

    @patch("dashboard.services.power.run_command")
    def test_scheduled_shutdown_empty_output(self, mock_cmd):
        mock_cmd.return_value = (0, "", "")
        res = power.get_scheduled_shutdown()
        assert res["scheduled"] is False
        assert res["details"] is None

    @patch("dashboard.services.power.run_command")
    def test_scheduled_shutdown_exception(self, mock_cmd):
        """get_scheduled_shutdown() does not catch exceptions — they propagate."""
        mock_cmd.side_effect = OSError("command not found")
        with pytest.raises(OSError, match="command not found"):
            power.get_scheduled_shutdown()
