"""
Unit tests for device_info service and /api/device/info endpoint.
Covers the multi-fallback detection paths in get_device_model().
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock
from dashboard.main import app


class TestGetDeviceModel:
    """get_device_model() fallback chain, tested source 1-6."""

    def test_device_tree_model_wins(self, tmp_path):
        """Device Tree model is the highest-priority source."""
        dt = tmp_path / "model"
        dt.write_bytes(b"Xiaomi Lavender\x00")
        with patch("dashboard.services.device_info.os.path.exists", return_value=True):
            with patch(
                "builtins.open",
                return_value=MagicMock(
                    __enter__=MagicMock(
                        return_value=MagicMock(
                            read=MagicMock(return_value=b"Xiaomi Lavender\x00")
                        )
                    ),
                    __exit__=MagicMock(return_value=False),
                ),
            ):
                from dashboard.services.device_info import get_device_model

                assert get_device_model() == "Xiaomi Lavender"

    def test_device_tree_read_error_falls_through(self):
        """A read error on the DT model path falls through to other sources."""

        def fake_exists(p):
            return p in ("/sys/firmware/devicetree/base/model", "/etc/os-release")

        with patch(
            "dashboard.services.device_info.os.path.exists", side_effect=fake_exists
        ):
            with patch("builtins.open", side_effect=OSError("EIO")):
                with patch(
                    "dashboard.services.device_info.subprocess.check_output",
                    side_effect=OSError,
                ):
                    with patch(
                        "dashboard.services.device_info.socket.gethostname",
                        return_value="myhost",
                    ):
                        from dashboard.services.device_info import get_device_model

                        assert get_device_model() == "myhost"

    def test_deviceinfo_name_source(self):
        """postmarketOS /etc/deviceinfo provides the model name."""
        content = '# deviceinfo\nboard_name=sdm660\ndeviceinfo_name="Xiaomi Lavender"\n'
        opened = MagicMock()
        opened.__enter__.return_value.__iter__ = MagicMock(
            return_value=iter(content.splitlines(keepends=True))
        )
        with patch(
            "dashboard.services.device_info.os.path.exists",
            side_effect=lambda p: p == "/etc/deviceinfo",
        ):
            with patch("builtins.open", return_value=opened):
                with patch(
                    "dashboard.services.device_info.subprocess.check_output",
                    side_effect=OSError,
                ):
                    with patch(
                        "dashboard.services.device_info.socket.gethostname",
                        return_value="myhost",
                    ):
                        from dashboard.services.device_info import get_device_model

                        assert get_device_model() == "Xiaomi Lavender"

    def test_dmi_generic_name_skipped(self):
        """DMI values like 'Default string' are skipped, hostname used."""
        dmi_files = {
            "/sys/class/dmi/id/product_name": "Default string",
            "/sys/devices/virtual/dmi/id/product_name": "none",
            "/sys/class/dmi/id/board_name": "O.E.M.",
        }
        opened = MagicMock()
        opened.__enter__.return_value.read.return_value = "Default string\n"
        with patch(
            "dashboard.services.device_info.os.path.exists",
            side_effect=lambda p: p in dmi_files,
        ):
            with patch("builtins.open", return_value=opened):
                with patch(
                    "dashboard.services.device_info.subprocess.check_output",
                    side_effect=OSError,
                ):
                    with patch(
                        "dashboard.services.device_info.socket.gethostname",
                        return_value="myhost",
                    ):
                        from dashboard.services.device_info import get_device_model

                        assert get_device_model() == "myhost"

    def test_dmi_repeated_suffix_cleaned(self):
        """'Lavender_Lavender' style DMI names get de-duplicated."""
        with patch(
            "dashboard.services.device_info.os.path.exists",
            side_effect=lambda p: p == "/sys/class/dmi/id/product_name",
        ):
            with patch(
                "builtins.open",
                return_value=MagicMock(
                    __enter__=MagicMock(
                        return_value=MagicMock(
                            read=MagicMock(return_value="Lavender_Lavender\n")
                        )
                    ),
                    __exit__=MagicMock(return_value=False),
                ),
            ):
                from dashboard.services.device_info import get_device_model

                assert get_device_model() == "Lavender"

    def test_hostnamectl_model_source(self):
        """hostnamectl Hardware Model output is used when sysfs is absent."""
        hostnamectl_out = (
            "   Static hostname: myhost\n"
            "       Hardware Model: Some Laptop Model\n"
            "     Chassis: laptop\n"
        )
        with patch("dashboard.services.device_info.os.path.exists", return_value=False):
            with patch(
                "dashboard.services.device_info.subprocess.check_output",
                return_value=hostnamectl_out,
            ):
                from dashboard.services.device_info import get_device_model

                assert get_device_model() == "Some Laptop Model"

    def test_machine_info_fallback(self):
        """/etc/machine-info PRETTY_HOSTNAME is used when nothing else exists."""
        content = '# machine-info\nPRETTY_HOSTNAME="My Pretty Host"\n'
        opened = MagicMock()
        opened.__enter__.return_value.__iter__ = MagicMock(
            return_value=iter(content.splitlines(keepends=True))
        )
        with patch(
            "dashboard.services.device_info.os.path.exists",
            side_effect=lambda p: p == "/etc/machine-info",
        ):
            with patch("builtins.open", return_value=opened):
                with patch(
                    "dashboard.services.device_info.subprocess.check_output",
                    side_effect=OSError,
                ):
                    with patch(
                        "dashboard.services.device_info.socket.gethostname",
                        return_value="",
                    ):
                        from dashboard.services.device_info import get_device_model

                        assert get_device_model() == "My Pretty Host"

    def test_hostname_fallback(self):
        """Socket hostname is the final fallback before platform.node()."""
        with patch("dashboard.services.device_info.os.path.exists", return_value=False):
            with patch(
                "dashboard.services.device_info.subprocess.check_output",
                side_effect=OSError,
            ):
                with patch(
                    "dashboard.services.device_info.socket.gethostname",
                    return_value="fallback-host",
                ):
                    from dashboard.services.device_info import get_device_model

                    assert get_device_model() == "fallback-host"

    def test_platform_node_last_resort(self):
        """platform.node() is the very last fallback."""
        with patch("dashboard.services.device_info.os.path.exists", return_value=False):
            with patch(
                "dashboard.services.device_info.subprocess.check_output",
                side_effect=OSError,
            ):
                with patch(
                    "dashboard.services.device_info.socket.gethostname",
                    return_value="localhost",
                ):
                    with patch(
                        "dashboard.services.device_info.platform.node",
                        return_value="node-host",
                    ):
                        from dashboard.services.device_info import get_device_model

                        assert get_device_model() == "node-host"


class TestGetOsInfo:
    """get_os_info() parsing of os-release."""

    def test_parses_os_release(self, tmp_path):
        content = (
            'NAME="Alpine Linux"\n'
            "ID=alpine\n"
            "VERSION_ID=3.20\n"
            'PRETTY_NAME="Alpine Linux v3.20"\n'
            "# comment line\n"
            "invalid=no-equals\n"
        )
        opened = MagicMock()
        opened.__enter__.return_value.__iter__ = MagicMock(
            return_value=iter(content.splitlines(keepends=True))
        )
        with patch(
            "dashboard.services.device_info.os.path.exists",
            side_effect=lambda p: p == "/etc/os-release",
        ):
            with patch("builtins.open", return_value=opened):
                from dashboard.services.device_info import get_os_info

                info = get_os_info()
                assert info["name"] == "Alpine Linux"
                assert info["id"] == "alpine"
                assert info["version"] == "3.20"

    def test_missing_os_release_uses_platform(self):
        """Missing os-release files fall back to platform.system()."""
        with patch("dashboard.services.device_info.os.path.exists", return_value=False):
            from dashboard.services.device_info import get_os_info

            info = get_os_info()
            assert "name" in info
            assert "id" in info

    def test_unreadable_os_release_uses_platform(self):
        """Unreadable os-release files fall back to platform.system()."""
        with patch(
            "dashboard.services.device_info.os.path.exists",
            side_effect=lambda p: p == "/etc/os-release",
        ):
            with patch("builtins.open", side_effect=PermissionError):
                from dashboard.services.device_info import get_os_info

                info = get_os_info()
                assert info["name"]  # falls back to platform.system()


class TestDeviceInfoEndpoint:
    """/api/device/info endpoint behavior."""

    @pytest.mark.asyncio
    async def test_device_info_public(self):
        """Test /api/device/info works without authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with patch("dashboard.api.device.get_system_info") as mock_info:
                mock_info.return_value = {
                    "model": "Test Device",
                    "os_name": "Test OS",
                    "os_pretty": "Test OS 1.0",
                    "os_version": "1.0",
                    "os_id": "testos",
                    "kernel": "6.0.0",
                    "arch": "aarch64",
                    "hostname": "testhost",
                }
                response = await client.get("/api/device/info")
                assert response.status_code == 200
                data = response.json()
                assert data["model"] == "Test Device"
                assert data["arch"] == "aarch64"
