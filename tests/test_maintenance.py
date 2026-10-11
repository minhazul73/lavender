"""
Unit tests covering maintenance/cronjob workflows, failure handling, and previously untested modules.
"""
import pytest
from unittest.mock import patch, MagicMock
import json
import os

from dashboard.services.battery import get_battery_info, THERMAL_NAME_MAP
from dashboard.services.processes import get_top_processes
from dashboard.services.systemd import list_services


class TestMaintenanceFailurePathsAndServices:
    """Test maintenance expected failure paths, mock external system tools, and untested service modules."""

    @patch("dashboard.services.battery.run_command")
    def class_battery_mock(self, mock_run_command):
        pass

    def test_battery_info_failure_handling(self):
        """Test get_battery_info gracefully handles upower failure or missing binary."""
        with patch("dashboard.services.battery.run_command", return_value=(1, "", "Command not found")):
            info = get_battery_info()
            assert "error" in info or info.get("note") == "No battery detected"

    @patch("dashboard.services.battery.run_command")
    def test_battery_info_parsing(self, mock_run_command):
        """Test get_battery_info correctly parses upower output."""
        mock_run_command.side_effect = [
            (0, "  native-path:  qcom_battery\n  device: /org/freedesktop/UPower/devices/battery_qcom_battery\n", ""),
            (0, "  native-path:          qcom_battery\n  vendor:               Qualcomm\n  model:                SDM660\n  state:                discharging\n  percentage:           85%\n  voltage:              3.8V\n  energy:               10.5 Wh\n", "")
        ]
        info = get_battery_info()
        assert info["percentage"] == 85
        assert info["state"] == "discharging"
        assert info["voltage"] == 3.8
        assert info["vendor"] == "Qualcomm"

    @patch("dashboard.services.processes.run_command")
    def test_process_list_failure_handling(self, mock_run_command):
        """Test get_top_processes gracefully handles ps failure or missing binary."""
        mock_run_command.return_value = (1, "", "ps command failed")
        procs = get_top_processes()
        assert isinstance(procs, list)
        assert len(procs) == 1
        assert "error" in procs[0]

    @patch("dashboard.services.systemd.run_command")
    def test_systemd_services_failure_handling(self, mock_run_command):
        """Test list_services handles systemctl failure gracefully."""
        mock_run_command.return_value = (1, "", "systemctl not available")
        services = list_services()
        assert isinstance(services, list)
        assert len(services) == 0

    def test_thermal_name_mapping(self):
        """Validate thermal sensor name mappings exist and cover key sensors."""
        assert "aoss_thermal" in THERMAL_NAME_MAP
        assert "cpu0_thermal" in THERMAL_NAME_MAP
        assert "gpu_thermal" in THERMAL_NAME_MAP
        assert THERMAL_NAME_MAP["gpu_thermal"] == "GPU (Adreno)"
