"""
Unit tests for dashboard.services.power.
"""
from unittest.mock import patch

from dashboard.services import power


class TestReboot:
    @patch("dashboard.services.power.run_sudo_command")
    def test_reboot_success(self, mock_sudo):
        mock_sudo.return_value = (0, "", "")
        res = power.reboot()
        assert res["action"] == "reboot"
        assert res["success"] is True
        assert res["error"] == ""

    @patch("dashboard.services.power.run_sudo_command")
    def test_reboot_failure(self, mock_sudo):
        mock_sudo.return_value = (1, "", "Failed to reboot")
        res = power.reboot()
        assert res["success"] is False
        assert res["error"] == "Failed to reboot"


class TestPoweroff:
    @patch("dashboard.services.power.run_sudo_command")
    def test_poweroff_success(self, mock_sudo):
        mock_sudo.return_value = (0, "System powering off", "")
        res = power.poweroff()
        assert res["action"] == "poweroff"
        assert res["success"] is True
        assert res["output"] == "System powering off"

    @patch("dashboard.services.power.run_sudo_command")
    def test_poweroff_failure(self, mock_sudo):
        mock_sudo.return_value = (1, "", "Permission denied")
        res = power.poweroff()
        assert res["success"] is False
        assert res["error"] == "Permission denied"


class TestSuspend:
    @patch("dashboard.services.power.run_sudo_command")
    def test_suspend_success(self, mock_sudo):
        mock_sudo.return_value = (0, "", "")
        res = power.suspend()
        assert res["action"] == "suspend"
        assert res["success"] is True

    @patch("dashboard.services.power.run_sudo_command")
    def test_suspend_failure(self, mock_sudo):
        mock_sudo.return_value = (1, "", "Suspend failed")
        res = power.suspend()
        assert res["success"] is False
        assert res["error"] == "Suspend failed"


class TestScheduledShutdown:
    @patch("dashboard.services.power.run_command")
    def test_scheduled_shutdown_active(self, mock_run):
        mock_run.return_value = (0, "Shutdown scheduled for Tue 15:00", "")
        res = power.get_scheduled_shutdown()
        assert res["scheduled"] is True
        assert "Shutdown scheduled" in res["details"]

    @patch("dashboard.services.power.run_command")
    def test_no_scheduled_shutdown(self, mock_run):
        mock_run.return_value = (1, "", "")
        res = power.get_scheduled_shutdown()
        assert res["scheduled"] is False
        assert res["details"] is None

    @patch("dashboard.services.power.run_command")
    def test_empty_output_treated_as_no_shutdown(self, mock_run):
        mock_run.return_value = (0, "", "")
        res = power.get_scheduled_shutdown()
        assert res["scheduled"] is False


class TestSchedulePowerAction:
    @patch("dashboard.services.power.run_sudo_command")
    def test_schedule_reboot(self, mock_sudo):
        mock_sudo.return_value = (0, "Shutdown scheduled", "")
        res = power.schedule_power_action("reboot", 5, "System maintenance")
        assert res["success"] is True
        assert res["action"] == "reboot"
        assert res["minutes"] == 5
        # Verify the command uses -r flag
        called_cmd = mock_sudo.call_args[0][0]
        assert called_cmd[0] == "shutdown"
        assert "-r" in called_cmd
        assert "+5" in called_cmd
        assert "System maintenance" in called_cmd

    @patch("dashboard.services.power.run_sudo_command")
    def test_schedule_poweroff_no_message(self, mock_sudo):
        mock_sudo.return_value = (0, "", "")
        res = power.schedule_power_action("poweroff", 10)
        assert res["success"] is True
        assert res["action"] == "poweroff"
        called_cmd = mock_sudo.call_args[0][0]
        assert "-h" in called_cmd
        assert "+10" in called_cmd

    @patch("dashboard.services.power.run_sudo_command")
    def test_schedule_failure(self, mock_sudo):
        mock_sudo.return_value = (1, "", "Invalid time")
        res = power.schedule_power_action("reboot", 0)
        assert res["success"] is False
        assert res["error"] == "Invalid time"


class TestCancelScheduledAction:
    @patch("dashboard.services.power.run_sudo_command")
    def test_cancel_success(self, mock_sudo):
        mock_sudo.return_value = (0, "Shutdown cancelled", "")
        res = power.cancel_scheduled_action()
        assert res["success"] is True
        assert res["output"] == "Shutdown cancelled"

    @patch("dashboard.services.power.run_sudo_command")
    def test_cancel_failure(self, mock_sudo):
        mock_sudo.return_value = (1, "", "No scheduled shutdown")
        res = power.cancel_scheduled_action()
        assert res["success"] is False
        assert res["error"] == "No scheduled shutdown"
