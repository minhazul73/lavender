"""
Unit tests for dashboard service modules.
"""

import pytest
from unittest.mock import patch, MagicMock

from dashboard.services.device_info import (
    get_device_model,
    get_os_info,
    get_system_info,
)
from dashboard.services.storage import (
    get_disk_usage,
    get_mounts,
    _is_external_mount,
    _parse_pct,
)
from dashboard.services.network import format_bytes, get_known_dns_provider
from dashboard.services.packages import get_package_manager, NullPackageManager
from dashboard.services.power import reboot, poweroff, suspend, get_scheduled_shutdown


class TestDeviceInfoService:
    """Test device_info service functions."""

    def test_get_system_info_structure(self):
        """Test system info returns dict with expected keys."""
        info = get_system_info()
        assert isinstance(info, dict)
        assert "model" in info
        assert "os_name" in info
        assert "kernel" in info
        assert "arch" in info
        assert "hostname" in info

    def test_get_os_info(self):
        """Test OS info retrieval."""
        os_info = get_os_info()
        assert isinstance(os_info, dict)
        assert "name" in os_info
        assert "pretty_name" in os_info


class TestStorageService:
    """Test storage service functions."""

    def test_parse_pct(self):
        """Test percentage string parsing."""
        assert _parse_pct("45%") == 45
        assert _parse_pct("0%") == 0
        assert _parse_pct("100%") == 100
        assert _parse_pct("invalid") == 0

    def test_is_external_mount(self):
        """Test external mount detection."""
        assert _is_external_mount("/mnt/sdcard") is True
        assert _is_external_mount("/media/usb") is True
        assert _is_external_mount("/boot") is False
        assert _is_external_mount("/") is False

    @patch("dashboard.services.storage._run_df")
    def test_get_disk_usage(self, mock_run_df):
        """Test get_disk_usage returns df entries."""
        mock_run_df.return_value = [
            {
                "fs": "/dev/sda1",
                "size": "100G",
                "used": "40G",
                "avail": "60G",
                "use_pct": "40%",
                "mount": "/",
                "is_external": False,
                "pct_num": 40,
            }
        ]
        disks = get_disk_usage()
        assert len(disks) == 1
        assert disks[0]["mount"] == "/"


class TestNetworkService:
    """Test network service functions."""

    def test_format_bytes(self):
        """Test byte formatting to human readable strings."""
        assert format_bytes(0) == "0 B"
        assert format_bytes(500) == "500 B"
        assert format_bytes(1024) == "1.0 KB"
        assert format_bytes(1048576) == "1.0 MB"
        assert format_bytes(1073741824) == "1.0 GB"

    def test_get_known_dns_provider(self):
        """Test DNS provider resolution."""
        assert get_known_dns_provider("1.1.1.1") == "Cloudflare DNS"
        assert get_known_dns_provider("8.8.8.8") == "Google Public DNS"
        assert get_known_dns_provider("9.9.9.9") == "Quad9"
        assert get_known_dns_provider("127.0.0.1") == "Local Stub Resolver"
        assert get_known_dns_provider("192.168.1.1") == "Local Router / Gateway"

    def test_primary_interface_prioritizes_wifi_ethernet_usb_over_tailscale(
        self, monkeypatch
    ):
        """Test that WiFi, Ethernet, and USB interfaces are prioritized over Tailscale."""
        from dashboard.services.live import NetworkRateCollector

        collector = NetworkRateCollector()

        # Mock operstate and default route on the class (due to __slots__)
        monkeypatch.setattr(
            NetworkRateCollector,
            "_interface_operstate",
            staticmethod(
                lambda iface: (
                    "up"
                    if iface in ("wlan0", "eth0", "usb0")
                    else ("down" if iface == "enp0" else "unknown")
                )
            ),
        )
        monkeypatch.setattr(
            NetworkRateCollector,
            "_default_route_interface",
            staticmethod(lambda: "wlan0"),
        )

        # Scenario 1: Tailscale vs WiFi (both have traffic)
        counters = {
            "tailscale0": (50000, 20000),
            "wlan0": (1000000, 500000),
            "lo": (10000, 10000),
        }
        assert collector._primary_interface(counters) == "wlan0"

        # Scenario 2: Tailscale vs USB tethering
        monkeypatch.setattr(
            NetworkRateCollector,
            "_default_route_interface",
            staticmethod(lambda: "usb0"),
        )
        counters = {
            "tailscale0": (50000, 20000),
            "usb0": (800000, 400000),
        }
        assert collector._primary_interface(counters) == "usb0"

        # Scenario 3: Tailscale vs Ethernet
        monkeypatch.setattr(
            NetworkRateCollector,
            "_default_route_interface",
            staticmethod(lambda: "eth0"),
        )
        counters = {
            "tailscale0": (50000, 20000),
            "eth0": (900000, 300000),
        }
        assert collector._primary_interface(counters) == "eth0"

        # Scenario 4: WiFi is up with 0 bytes, Tailscale has traffic -> WiFi
        # still preferred
        monkeypatch.setattr(
            NetworkRateCollector,
            "_default_route_interface",
            staticmethod(lambda: "wlan0"),
        )
        counters = {
            "tailscale0": (50000, 20000),
            "wlan0": (0, 0),
        }
        assert collector._primary_interface(counters) == "wlan0"

        # Scenario 5: Physical interfaces are down with 0 bytes, only Tailscale
        # is active
        monkeypatch.setattr(
            NetworkRateCollector, "_default_route_interface", staticmethod(lambda: None)
        )
        monkeypatch.setattr(
            NetworkRateCollector,
            "_interface_operstate",
            staticmethod(
                lambda iface: "down" if iface in ("wlan0", "usb0") else "unknown"
            ),
        )
        counters = {
            "tailscale0": (50000, 20000),
            "wlan0": (0, 0),
            "usb0": (0, 0),
        }
        assert collector._primary_interface(counters) == "tailscale0"


class TestPackagesService:
    """Test packages service functions."""

    def test_get_package_manager_none_detected(self, monkeypatch):
        """Test fallback when no package manager binary exists."""
        import dashboard.services.packages as pkgs

        monkeypatch.setattr(pkgs, "_CURRENT_MANAGER", None)
        monkeypatch.setattr(pkgs.shutil, "which", lambda _name: None)
        mgr = get_package_manager()
        assert mgr.id == "none"

    @patch("dashboard.services.storage._run_df", side_effect=RuntimeError("df failed"))
    def test_get_disk_usage_failure(self, _mock):
        assert get_disk_usage() == []

    @patch("dashboard.services.power.run_sudo_command")
    def test_reboot_failure(self, mock_sudo):
        mock_sudo.return_value = (1, "", "Interactive authentication required.")
        res = reboot()
        assert res["success"] is False
        assert res["error"] == "Interactive authentication required."


class TestPowerService:
    """Test power service functions."""

    @patch("dashboard.services.power.run_sudo_command")
    def test_reboot(self, mock_sudo):
        """Test reboot returns expected dict structure."""
        mock_sudo.return_value = (0, "Rebooting", "")
        res = reboot()
        assert res["action"] == "reboot"
        assert res["success"] is True

    @patch("dashboard.services.power.run_command")
    def test_get_scheduled_shutdown_none(self, mock_cmd):
        """Test checking scheduled shutdown when none is active."""
        mock_cmd.return_value = (1, "", "")
        res = get_scheduled_shutdown()
        assert res["scheduled"] is False


class TestSystemdService:
    """Test systemd service functions."""

    @patch("dashboard.services.systemd.run_command")
    def test_get_recent_logs_parses_realtime_timestamp(self, mock_cmd):
        import json
        from dashboard.services.systemd import get_recent_logs

        mock_entry = {
            "__REALTIME_TIMESTAMP": "1792166401792781",
            "MESSAGE": "usb 1-4: new high-speed USB device",
            "PRIORITY": "6",
            "_SYSTEMD_UNIT": "systemd-udevd.service",
        }
        mock_cmd.return_value = (0, json.dumps(mock_entry), "")
        logs = get_recent_logs(lines=1)
        assert len(logs) == 1
        log = logs[0]
        assert "T" in log["timestamp"]
        assert "+00:00" in log["timestamp"] or "Z" in log["timestamp"]
        assert log["service"] == "systemd-udevd.service"
        assert log["level"] == "info"
        assert "usb 1-4" in log["message"]

    @patch("dashboard.services.systemd.run_command")
    def test_get_recent_logs_fallback_syslog_timestamp(self, mock_cmd):
        import json
        from dashboard.services.systemd import get_recent_logs

        mock_entry = {
            "SYSLOG_TIMESTAMP": "Oct 16 22:00:01 ",
            "MESSAGE": "CRON[123]: job done",
            "PRIORITY": "4",
            "SYSLOG_IDENTIFIER": "CRON",
        }
        mock_cmd.return_value = (0, json.dumps(mock_entry), "")
        logs = get_recent_logs(lines=1)
        assert len(logs) == 1
        log = logs[0]
        assert log["timestamp"] == "Oct 16 22:00:01 "
        assert log["service"] == "CRON"
        assert log["level"] == "warning"
