"""
Unit tests for get_wifi_info() failure and edge-case paths in network.py.
"""

from unittest.mock import patch
from dashboard.services.network import (
    get_wifi_info,
    format_bytes,
    get_known_dns_provider,
)


class TestGetWifiInfo:
    """get_wifi_info() failure scenarios and edge cases."""

    def test_no_wifi_hardware(self):
        """Test get_wifi_info when no WiFi hardware exists."""
        with patch("os.path.exists", return_value=False):
            result = get_wifi_info()
            assert result["has_hardware"] is False
            assert result["connected"] is False
            assert "message" in result
            assert result["available_interfaces"] == []

    def test_wifi_hardware_found_but_no_commands(self):
        """Test WiFi hardware exists but no CLI tools available."""

        def fake_exists(path):
            if path == "/sys/class/net":
                return True
            if path == "/sys/class/net/wlan0/wireless":
                return True
            return False

        with patch("os.path.exists", side_effect=fake_exists):
            with patch("os.listdir", return_value=["wlan0"]):
                with patch("dashboard.services.network.which", return_value=None):
                    result = get_wifi_info()
                    assert result["has_hardware"] is True
                    assert result["available_interfaces"] == ["wlan0"]
                    assert result["interface"] == "wlan0"
                    assert result["connected"] is False

    def test_wifi_nmcli_unavailable_fallback(self):
        """Test WiFi info when nmcli is not available but iwconfig is."""

        def fake_exists(path):
            if path == "/sys/class/net":
                return True
            if path == "/sys/class/net/wlan0/wireless":
                return True
            return False

        with patch("os.path.exists", side_effect=fake_exists):
            with patch("os.listdir", return_value=["wlan0"]):
                with patch(
                    "dashboard.services.network.which",
                    side_effect=lambda cmd: (
                        "/usr/bin/iwconfig" if cmd == "iwconfig" else None
                    ),
                ):
                    with patch(
                        "dashboard.services.network.run_command",
                        return_value=(
                            0,
                            'wlan0  IEEE 802.11bg  ESSID:"MyWifi"\n'
                            "\tMode:Managed  Frequency:2.437 GHz",
                            "",
                        ),
                    ):
                        result = get_wifi_info()
                        assert result["has_hardware"] is True
                        assert result["connected"] is True
                        assert result["ssid"] == "MyWifi"


class TestFormatBytes:
    """format_bytes() edge cases."""

    def test_zero_bytes(self):
        assert format_bytes(0) == "0 B"

    def test_small_bytes(self):
        assert format_bytes(500) == "500 B"

    def test_kilobytes(self):
        assert format_bytes(1500) == "1.5 KB"

    def test_megabytes(self):
        assert format_bytes(2048 * 1024) == "2.0 MB"

    def test_gigabytes(self):
        assert format_bytes(3 * 1024**3) == "3.0 GB"


class TestGetKnownDnsProvider:
    """get_known_dns_provider() edge cases."""

    def test_google_dns(self):
        assert get_known_dns_provider("8.8.8.8") == "Google Public DNS"

    def test_cloudflare_dns(self):
        assert get_known_dns_provider("1.1.1.1") == "Cloudflare DNS"

    def test_private_ip_is_local_router(self):
        assert get_known_dns_provider("192.168.1.1") == "Local Router / Gateway"

    def test_empty_string(self):
        assert get_known_dns_provider("") == "Unknown"

    def test_local_stub_resolver(self):
        assert get_known_dns_provider("127.0.0.53") == "Local Stub Resolver"

    def test_unlisted_ip_is_isp(self):
        assert get_known_dns_provider("203.0.113.9") == "ISP / Custom DNS"
