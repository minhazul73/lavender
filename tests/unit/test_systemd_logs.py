import json
from unittest.mock import patch
from server.services.systemd import get_recent_logs


def test_get_recent_logs_parses_realtime_timestamp():
    # Mock journalctl JSON output with microseconds since epoch
    mock_entry = {
        "__REALTIME_TIMESTAMP": "1792166401792781",
        "MESSAGE": "usb 1-4: new high-speed USB device",
        "PRIORITY": "6",
        "_SYSTEMD_UNIT": "systemd-udevd.service",
    }
    raw_output = json.dumps(mock_entry)

    with patch("server.services.systemd.run_command", return_value=(0, raw_output, "")):
        logs = get_recent_logs(lines=1)
        assert len(logs) == 1
        log = logs[0]
        # Should be formatted as ISO-8601 UTC timestamp containing T and +00:00 (or Z)
        assert "T" in log["timestamp"]
        assert "+00:00" in log["timestamp"] or "Z" in log["timestamp"]
        assert log["service"] == "systemd-udevd.service"
        assert log["level"] == "info"
        assert "usb 1-4" in log["message"]


def test_get_recent_logs_fallback_syslog_timestamp():
    mock_entry = {
        "SYSLOG_TIMESTAMP": "Oct 16 22:00:01 ",
        "MESSAGE": "CRON[123]: (root) CMD (run-parts /etc/cron.hourly)",
        "PRIORITY": "4",
        "SYSLOG_IDENTIFIER": "CRON",
    }
    raw_output = json.dumps(mock_entry)

    with patch("server.services.systemd.run_command", return_value=(0, raw_output, "")):
        logs = get_recent_logs(lines=1)
        assert len(logs) == 1
        log = logs[0]
        assert log["timestamp"] == "Oct 16 22:00:01 "
        assert log["service"] == "CRON"
        assert log["level"] == "warning"


def test_get_recent_logs_command_failure():
    with patch("server.services.systemd.run_command", return_value=(1, "", "Failed")):
        logs = get_recent_logs(lines=5)
        assert logs == []
