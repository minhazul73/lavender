"""
Unit tests for dashboard/services/battery.py — failure and edge-case scenarios.
"""

from unittest.mock import patch, MagicMock

from dashboard.services import battery


class TestGetBatteryInfo:
    @patch("dashboard.services.battery.run_command")
    def test_upower_not_available(self, mock_cmd):
        """Test battery info when upower -i fails (no battery / no upower)."""
        # upower -e returns nothing, upower -i fails
        mock_cmd.side_effect = [
            (1, "", "upower: command not found"),
            (1, "", "upower: command not found"),
        ]
        result = battery.get_battery_info()
        assert "error" in result
        assert "note" in result
        assert "battery" in result["note"].lower() or "upower" in result["note"].lower()

    @patch("dashboard.services.battery.run_command")
    def test_upower_no_battery_path_found(self, mock_cmd):
        """Test fallback to known battery path when no battery device listed."""
        # upower -e finds no battery, upower -i fails on known path
        mock_cmd.side_effect = [
            (0, "/org/freedesktop/UPower/devices/line_power_AC\n", ""),
            (1, "", "UPower error: device not found"),
        ]
        result = battery.get_battery_info()
        assert "error" in result
        assert "note" in result

    @patch("dashboard.services.battery.run_command")
    def test_empty_upower_output(self, mock_cmd):
        """Test parsing upower output with empty lines."""
        mock_cmd.side_effect = [
            (0, "/org/freedesktop/UPower/devices/battery_qcom_battery\n", ""),
            (0, "", ""),
        ]
        result = battery.get_battery_info()
        assert result["percentage"] is None
        assert result["state"] is None
        assert "No battery detected" in result["note"]

    @patch("dashboard.services.battery.run_command")
    def test_malformed_percentage_value(self, mock_cmd):
        """Test graceful handling of malformed numeric values."""
        mock_cmd.side_effect = [
            (0, "/org/freedesktop/UPower/devices/battery_qcom_battery\n", ""),
            (
                0,
                "  percentage: N/A\n" "  voltage: 4.0V\n" "  capacity: 85.0%\n",
                "",
            ),
        ]
        result = battery.get_battery_info()
        assert result["percentage"] is None  # N/A doesn't parse
        assert result["voltage"] == 4.0
        assert result["capacity"] == 85.0

    @patch("dashboard.services.battery.run_command")
    def test_valid_battery_output(self, mock_cmd):
        """Test full valid upower output parses correctly."""
        mock_cmd.side_effect = [
            (0, "/org/freedesktop/UPower/devices/battery_qcom_battery\n", ""),
            (
                0,
                "  state: charging\n"
                "  percentage: 85%\n"
                "  voltage: 4.0V\n"
                "  capacity: 85.0%\n"
                "  temperature: 31.5 degrees C\n"
                "  vendor: QCOM\n"
                "  model: qcom-battery\n",
                "",
            ),
        ]
        result = battery.get_battery_info()
        assert result["state"] == "charging"
        assert result["percentage"] == 85
        assert result["voltage"] == 4.0
        assert result["capacity"] == 85.0
        assert result["temperature"] == 31.5
        assert result["vendor"] == "QCOM"
        assert result["model"] == "qcom-battery"

    @patch("dashboard.services.battery.run_command")
    def test_line_power_filtered(self, mock_cmd):
        """Test that line_power entries are not treated as batteries."""
        mock_cmd.side_effect = [
            (0, "/org/freedesktop/UPower/devices/line_power_AC\n", ""),
            (1, "", "No such device"),
        ]
        result = battery.get_battery_info()
        # Falls through to known path which also fails
        assert "error" in result


class TestGetThermalZones:
    def test_no_thermal_dir(self):
        """Test when /sys/class/thermal doesn't exist."""
        with patch("os.path.isdir", return_value=False):
            zones = battery.get_thermal_zones()
            assert len(zones) == 1
            assert "note" in zones[0]

    def test_empty_thermal_dir(self):
        """Test empty thermal directory returns no zones."""
        with patch("os.path.isdir", return_value=True), patch(
            "os.listdir", return_value=[]
        ):
            zones = battery.get_thermal_zones()
            assert zones == []

    def test_zone_with_no_temp_file(self):
        """Test thermal zone that has type but no temp file."""
        with patch("os.listdir", return_value=["thermal_zone0"]), patch(
            "os.path.isdir", return_value=True
        ), patch("os.path.isfile", side_effect=lambda p: p.endswith("type")):
            with patch("builtins.open", create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = (
                    "aoss_thermal"
                )
                zones = battery.get_thermal_zones()
            assert len(zones) == 1
            assert zones[0]["temp_millicelsius"] is None
            assert zones[0]["temp_celsius"] is None


class TestGetCpuFrequencies:
    def test_no_cpu_dir(self, monkeypatch):
        """Test when /sys/devices/system/cpu doesn't exist."""
        with patch.object(battery.os, "path") as mock_path:
            mock_path.isdir.return_value = False
            mock_path.join = battery.os.path.join
            freqs = battery.get_cpu_frequencies()
            assert len(freqs) == 1
            assert "note" in freqs[0]

    def test_cpu_with_no_freq_files(self, monkeypatch, tmp_path):
        """Test CPU entry with no cpufreq data available."""
        with patch.object(
            battery.os, "listdir", return_value=["cpu0", "cpu1", "cpu2", "cpu3"]
        ), patch.object(battery.os.path, "isdir", return_value=True), patch.object(
            battery.os.path, "isfile", return_value=False
        ), patch.object(
            battery.os.path, "join", side_effect=battery.os.path.join
        ):
            freqs = battery.get_cpu_frequencies()
            assert len(freqs) == 4
            for f in freqs:
                assert f["frequency_khz"] is None
                assert f["frequency_mhz"] is None
                assert f["governor"] is None

    def test_non_numeric_entries_skipped(self, monkeypatch):
        """Test that non-CPU entries (like 'online', 'possible') are skipped."""
        with patch.object(
            battery.os, "listdir", return_value=["cpu0", "online", "possible", "power"]
        ), patch.object(battery.os.path, "isdir", return_value=True), patch.object(
            battery.os.path, "isfile", return_value=False
        ), patch.object(
            battery.os.path, "join", side_effect=battery.os.path.join
        ):
            freqs = battery.get_cpu_frequencies()
            assert len(freqs) == 1  # only cpu0
            assert freqs[0]["cpu"] == 0


class TestGetCpuScalingAvailable:
    def test_no_scaling_dir(self, monkeypatch):
        """Test when cpu0/cpufreq doesn't exist."""
        with patch.object(battery.os.path, "isdir", return_value=False):
            result = battery.get_cpu_scaling_available()
            assert result == {"governors": [], "min_freq": None, "max_freq": None}

    def test_all_scaling_files_present(self, monkeypatch):
        """Test full scaling data read from sysfs."""
        path_to_content = {
            (
                "/sys/devices/system/cpu/cpu0/cpufreq/" "scaling_available_governors"
            ): "performance conservative ondemand powersave",
            "/sys/devices/system/cpu/cpu0/cpufreq/scaling_min_freq": "300000",
            "/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq": "1800000",
        }

        def fake_open(path, mode="r"):
            f = MagicMock()
            f.__enter__.return_value.read.return_value = path_to_content.get(path, "")
            return f

        with patch.object(battery.os.path, "isdir", return_value=True), patch.object(
            battery.os.path, "isfile", return_value=True
        ), patch.object(
            battery.os.path, "join", side_effect=battery.os.path.join
        ), patch(
            "builtins.open", side_effect=fake_open
        ):
            result = battery.get_cpu_scaling_available()

        assert "performance" in result["governors"]
        assert result["min_freq"] == 300000
        assert result["max_freq"] == 1800000

    def test_scaling_read_error(self, monkeypatch):
        """Test graceful handling when sysfs reads fail."""
        with patch.object(battery.os.path, "isdir", return_value=True), patch.object(
            battery.os.path, "isfile", return_value=True
        ), patch.object(
            battery.os.path, "join", side_effect=battery.os.path.join
        ), patch(
            "builtins.open", side_effect=PermissionError("read denied")
        ):
            result = battery.get_cpu_scaling_available()
            # Should return empty defaults after exception
            assert result["governors"] == []
            assert result["min_freq"] is None
            assert result["max_freq"] is None


class TestGetUptime:
    def test_valid_uptime(self, monkeypatch):
        """Test uptime parsing from /proc/uptime."""
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = (
                "86400.5 172800.1\n"
            )
            result = battery.get_uptime()

        assert result["seconds"] == 86400.5
        assert "1d" in result["formatted"]

    def test_invalid_uptime_file(self, monkeypatch):
        """Test graceful handling when /proc/uptime is unreadable."""
        with patch("builtins.open", side_effect=FileNotFoundError("no /proc/uptime")):
            result = battery.get_uptime()
        assert result["seconds"] == 0.0
        assert result["formatted"] == "Unknown"

    def test_short_uptime(self):
        """Test uptime formatting for less than 1 hour."""
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = (
                "300.5 600.1\n"
            )
            result = battery.get_uptime()
        assert result["seconds"] == 300.5
        assert "5m" in result["formatted"]


class TestSetCpuGovernor:
    @patch("dashboard.services.battery.run_sudo_command")
    @patch("dashboard.services.battery.get_cpu_scaling_available")
    def test_invalid_governor_rejected(self, mock_avail, mock_sudo):
        """Test that unsupported governor is rejected before execution."""
        mock_avail.return_value = {"governors": ["performance", "powersave"]}
        result = battery.set_cpu_governor("invalid_gov")
        assert result["success"] is False
        assert "not supported" in result["error"]
        mock_sudo.assert_not_called()

    @patch("dashboard.services.battery.run_sudo_command")
    @patch("dashboard.services.battery.get_cpu_scaling_available")
    def test_cpupower_success(self, mock_avail, mock_sudo):
        """Test governor set via cpupower command."""
        mock_avail.return_value = {"governors": ["performance", "powersave"]}
        mock_sudo.return_value = (0, "Governor set", "")
        result = battery.set_cpu_governor("powersave")
        assert result["success"] is True
        assert result["governor"] == "powersave"
        mock_sudo.assert_called_once_with(
            ["cpupower", "frequency-set", "-g", "powersave"], timeout=10
        )

    @patch("dashboard.services.battery.run_sudo_command")
    @patch("dashboard.services.battery.get_cpu_scaling_available")
    def test_cpupower_fails_fallback_sysfs(self, mock_avail, mock_sudo):
        """Test fallback to sysfs write when cpupower fails."""
        mock_avail.return_value = {"governors": ["performance", "powersave"]}

        call_count = [0]

        def fake_sudo(cmd, timeout=10):
            call_count[0] += 1
            if call_count[0] == 1:
                # cpupower fails
                return (1, "", "cpupower: not found")
            # sysfs writes succeed
            return (0, "", "")

        mock_sudo.side_effect = fake_sudo

        with patch.object(
            battery.os, "listdir", return_value=["cpu0", "cpu1"]
        ), patch.object(battery.os.path, "isdir", return_value=True), patch.object(
            battery.os.path, "isfile", return_value=True
        ), patch.object(
            battery.os.path, "join", side_effect=battery.os.path.join
        ):
            result = battery.set_cpu_governor("powersave")

        assert result["success"] is True
        assert "2 CPU cores" in result["output"]

    @patch("dashboard.services.battery.run_sudo_command")
    @patch("dashboard.services.battery.get_cpu_scaling_available")
    def test_all_governor_writes_fail(self, mock_avail, mock_sudo):
        """Test failure when all write methods fail."""
        mock_avail.return_value = {"governors": ["performance", "powersave"]}
        mock_sudo.return_value = (1, "", "Operation not permitted")

        with patch.object(battery.os, "listdir", return_value=["cpu0"]), patch.object(
            battery.os.path, "isdir", return_value=True
        ), patch.object(battery.os.path, "isfile", return_value=True), patch.object(
            battery.os.path, "join", side_effect=battery.os.path.join
        ):
            result = battery.set_cpu_governor("powersave")

        assert result["success"] is False
        assert "Operation not permitted" in result["error"]

    @patch("dashboard.services.battery.run_sudo_command")
    @patch("dashboard.services.battery.get_cpu_scaling_available")
    def test_no_scaling_available_skips_validation(self, mock_avail, mock_sudo):
        """Test governor not validated when scaling data unavailable."""
        mock_avail.return_value = {"governors": []}
        mock_sudo.return_value = (0, "Set", "")
        result = battery.set_cpu_governor("any_governor")
        assert result["success"] is True

    @patch("dashboard.services.battery.run_sudo_command")
    @patch("dashboard.services.battery.get_cpu_scaling_available")
    def test_governor_is_lowercased(self, mock_avail, mock_sudo):
        """Test that governor name is normalized to lowercase."""
        mock_avail.return_value = {"governors": ["performance", "powersave"]}
        mock_sudo.return_value = (0, "Set", "")
        result = battery.set_cpu_governor("Powersave")
        assert result["success"] is True
        assert result["governor"] == "powersave"
