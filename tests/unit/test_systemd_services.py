"""
Unit tests for dashboard.services.systemd.
"""

import json
from unittest.mock import patch

from dashboard.services import systemd


class TestListServices:
    @patch("dashboard.services.systemd.run_command")
    def test_user_services_only(self, mock_run):
        out = (
            "jellyfin.service loaded active running Jellyfin\n"
            "qbittorrent.service loaded active running qBittorrent\n"
        )
        mock_run.return_value = (0, out, "")
        result = systemd.list_services(user_only=True)
        assert len(result) == 2
        assert result[0]["name"] == "jellyfin.service"
        assert result[0]["scope"] == "user"
        assert result[0]["active_state"] == "active"
        # system command should not be called
        assert mock_run.call_count == 1

    @patch("dashboard.services.systemd.run_sudo_command")
    @patch("dashboard.services.systemd.run_command")
    def test_system_services_fallback_to_sudo(self, mock_run, mock_sudo):
        mock_run.return_value = (1, "", "Permission denied")
        sys_out = "sshd.service loaded active running OpenSSH\n"
        mock_sudo.return_value = (0, sys_out, "")
        result = systemd.list_services(system_only=True)
        assert len(result) == 1
        assert result[0]["scope"] == "system"
        mock_sudo.assert_called_once()

    @patch("dashboard.services.systemd.run_command")
    def test_empty_output(self, mock_run):
        mock_run.return_value = (0, "", "")
        result = systemd.list_services(user_only=True)
        assert result == []


class TestGetServiceStatus:
    @patch("dashboard.services.systemd.run_command")
    def test_parses_status_output(self, mock_run):
        status_out = (
            "* jellyfin.service - Jellyfin Media Server\n"
            "     Loaded: loaded (/lib/systemd/system/jellyfin.service; enabled)\n"
            "     Active: active (running) since Mon 2026-10-27 10:00:00 UTC; 1h ago\n"
            "   Main PID: 1234 (jellyfin)\n"
            "      Tasks: 15\n"
            "     Memory: 256.0M\n"
            "        CPU: 5.2s\n"
            "       Docs: https://jellyfin.org\n"
        )
        mock_run.return_value = (0, status_out, "")
        info = systemd.get_service_status("jellyfin.service")
        assert info["name"] == "jellyfin.service"
        assert info["active"] is True
        assert info["active_state"] == "active"
        assert info["sub_state"] == "running"
        assert info["description"] == "Jellyfin Media Server"
        assert info["unit_file_state"] == "enabled"
        assert info["main_pid"] == 1234
        assert info["process_name"] == "jellyfin"
        assert info["tasks"] == "15"
        assert info["memory"] == "256.0M"
        assert info["cpu"] == "5.2s"
        assert info["docs"] == "https://jellyfin.org"

    @patch("dashboard.services.systemd.run_command")
    def test_inactive_service(self, mock_run):
        status_out = (
            "* foo.service - Foo Service\n"
            "     Loaded: loaded (/etc/systemd/system/foo.service; disabled)\n"
            "     Active: inactive (dead)\n"
        )
        mock_run.return_value = (0, status_out, "")
        info = systemd.get_service_status("foo.service")
        assert info["active"] is False
        assert info["active_state"] == "inactive"
        assert info["unit_file_state"] == "disabled"

    @patch("dashboard.services.systemd.run_sudo_command")
    @patch("dashboard.services.systemd.run_command")
    def test_sudo_fallback_on_empty_output(self, mock_run, mock_sudo):
        mock_run.return_value = (0, "", "")
        mock_sudo.return_value = (0, "* svc - Svc\n     Active: active (running)\n", "")
        info = systemd.get_service_status("svc")
        assert info["active"] is True
        mock_sudo.assert_called_once()

    @patch("dashboard.services.systemd.run_command")
    def test_user_service_flag(self, mock_run):
        mock_run.return_value = (0, "* svc - Svc\n", "")
        systemd.get_service_status("svc", user=True)
        cmd = mock_run.call_args[0][0]
        assert "--user" in cmd


class TestGetServiceLogs:
    @patch("dashboard.services.systemd.run_command")
    def test_returns_logs_on_success(self, mock_run):
        mock_run.return_value = (0, "line1\nline2\n", "")
        logs = systemd.get_service_logs("jellyfin.service", lines=10)
        assert "line1" in logs

    @patch("dashboard.services.systemd.run_sudo_command")
    @patch("dashboard.services.systemd.run_command")
    def test_falls_back_to_sudo(self, mock_run, mock_sudo):
        mock_run.return_value = (1, "", "No access")
        mock_sudo.return_value = (0, "log data\n", "")
        logs = systemd.get_service_logs("sshd.service")
        assert "log data" in logs
        mock_sudo.assert_called_once()

    @patch("dashboard.services.systemd.run_command")
    def test_returns_error_on_failure(self, mock_run):
        mock_run.return_value = (1, "", "journalctl failed")
        logs = systemd.get_service_logs("missing.service", user=True)
        assert logs == "journalctl failed"


class TestServiceAction:
    @patch("dashboard.services.systemd.run_command")
    def test_start_user_service(self, mock_run):
        mock_run.return_value = (0, "", "")
        res = systemd.service_action("jellyfin.service", "start", user=True)
        assert res["success"] is True
        assert res["action"] == "start"
        cmd = mock_run.call_args[0][0]
        assert "--user" in cmd
        assert "start" in cmd

    @patch("dashboard.services.systemd.run_sudo_command")
    @patch("dashboard.services.systemd.run_command")
    def test_system_action_falls_back_to_sudo(self, mock_run, mock_sudo):
        mock_run.return_value = (1, "", "Access denied")
        mock_sudo.return_value = (0, "", "")
        res = systemd.service_action("sshd.service", "restart", user=False)
        assert res["success"] is True
        mock_sudo.assert_called_once()

    @patch("dashboard.services.systemd.run_command")
    def test_action_failure(self, mock_run):
        mock_run.return_value = (1, "", "Failed to stop")
        res = systemd.service_action("foo.service", "stop", user=True)
        assert res["success"] is False
        assert res["error"] == "Failed to stop"


class TestServiceToggleEnabled:
    @patch("dashboard.services.systemd.service_action")
    def test_enable_calls_start_action(self, mock_action):
        mock_action.return_value = {"success": True}
        res = systemd.service_toggle_enabled("foo.service", enable=True)
        mock_action.assert_called_once_with("foo.service", "enable", False)
        assert res["success"] is True

    @patch("dashboard.services.systemd.service_action")
    def test_disable_calls_stop_action(self, mock_action):
        mock_action.return_value = {"success": True}
        systemd.service_toggle_enabled("foo.service", enable=False)
        mock_action.assert_called_once_with("foo.service", "disable", False)


class TestGetAllUnits:
    @patch("dashboard.services.systemd.run_sudo_command")
    @patch("dashboard.services.systemd.run_command")
    def test_combines_user_and_system(self, mock_run, mock_sudo):
        user_out = "jellyfin.service loaded active running\n"
        mock_run.return_value = (0, user_out, "")
        sys_out = "sshd.service loaded active running\n"
        mock_sudo.return_value = (0, sys_out, "")
        units = systemd.get_all_units()
        assert len(units) == 2
        scopes = {u["scope"] for u in units}
        assert "user" in scopes
        assert "system" in scopes


class TestGetRecentLogs:
    @patch("dashboard.services.systemd.run_command")
    def test_parses_json_entries(self, mock_run):
        entry1 = json.dumps(
            {
                "__REALTIME_TIMESTAMP": "1698400000000000",
                "MESSAGE": "Service started",
                "PRIORITY": 6,
                "_SYSTEMD_UNIT": "jellyfin.service",
            }
        )
        entry2 = json.dumps(
            {
                "__REALTIME_TIMESTAMP": "1698400001000000",
                "MESSAGE": "Error occurred",
                "PRIORITY": 3,
                "_COMM": "kernel",
            }
        )
        mock_run.return_value = (0, f"{entry1}\n{entry2}\n", "")
        logs = systemd.get_recent_logs(lines=10)
        assert len(logs) == 2
        assert logs[0]["message"] == "Service started"
        assert logs[0]["level"] == "info"
        assert logs[0]["service"] == "jellyfin.service"
        assert logs[1]["level"] == "warning"
        assert logs[1]["service"] == "kernel"

    @patch("dashboard.services.systemd.run_command")
    def test_truncates_long_messages(self, mock_run):
        long_msg = "x" * 300
        entry = json.dumps(
            {
                "__REALTIME_TIMESTAMP": "1698400000000000",
                "MESSAGE": long_msg,
                "PRIORITY": 6,
            }
        )
        mock_run.return_value = (0, f"{entry}\n", "")
        logs = systemd.get_recent_logs()
        assert len(logs[0]["message"]) == 201
        assert logs[0]["message"].endswith("\u2026")

    @patch("dashboard.services.systemd.run_command")
    def test_warning_level(self, mock_run):
        entry = json.dumps(
            {
                "MESSAGE": "warn",
                "PRIORITY": 4,
            }
        )
        mock_run.return_value = (0, f"{entry}\n", "")
        logs = systemd.get_recent_logs()
        assert logs[0]["level"] == "warning"

    @patch("dashboard.services.systemd.run_command")
    def test_command_failure_returns_empty(self, mock_run):
        mock_run.return_value = (1, "", "failed")
        logs = systemd.get_recent_logs()
        assert logs == []

    @patch("dashboard.services.systemd.run_command")
    def test_invalid_json_skipped(self, mock_run):
        mock_run.return_value = (0, "not json\n", "")
        logs = systemd.get_recent_logs()
        assert logs == []
