import unittest
from unittest.mock import patch, mock_open
from dashboard.services.battery import (
    get_battery_info,
    get_thermal_zones,
    get_cpu_frequencies,
    get_cpu_scaling_available,
    get_uptime,
    set_cpu_governor,
)


class TestBatteryServices(unittest.TestCase):
    @patch("dashboard.services.battery.run_command")
    def test_get_battery_info_success(self, mock_run_command):
        # Mock upower -e and upower -i
        mock_run_command.side_effect = [
            (0, "/org/freedesktop/UPower/devices/battery_BAT0\n", ""),
            (
                0,
                "  native-path:          BAT0\n"
                "  vendor:               TestVendor\n"
                "  model:                TestModel\n"
                "  power supply:         yes\n"
                "  updated:              Sat 24 Oct 2026 12:00:00 PM UTC (10s ago)\n"
                "  has history:          yes\n"
                "  has statistics:       yes\n"
                "  present:              yes\n"
                "  rechargeable:         yes\n"
                "  state:                charging\n"
                "  warning level:        none\n"
                "  energy:               45 Wh\n"
                "  energy-empty:         0 Wh\n"
                "  energy-full:          50 Wh\n"
                "  energy-full-design:   50 Wh\n"
                "  energy-rate:          10 W\n"
                "  voltage:              12.5 V\n"
                "  charge-cycles:        100\n"
                "  percentage:           90%\n"
                "  capacity:             100%\n"
                "  technology:           lithium-ion\n",
                "",
            ),
        ]
        info = get_battery_info()
        self.assertEqual(info["percentage"], 90)
        self.assertEqual(info["state"], "charging")
        self.assertEqual(info["voltage"], 12.5)
        self.assertEqual(info["energy"], 45.0)
        self.assertEqual(info["energy_full"], 50.0)
        self.assertEqual(info["energy_full_design"], 50.0)
        self.assertEqual(info["energy_rate"], 10.0)
        self.assertEqual(info["capacity"], 100.0)
        self.assertEqual(info["vendor"], "TestVendor")
        self.assertEqual(info["model"], "TestModel")
        self.assertEqual(info["technology"], "lithium-ion")
        self.assertEqual(info["charge_cycles"], 100)

    @patch("dashboard.services.battery.run_command")
    def test_get_battery_info_failure(self, mock_run_command):
        mock_run_command.return_value = (1, "", "Error")
        info = get_battery_info()
        self.assertIn("error", info)

    @patch("os.path.isdir")
    @patch("os.listdir")
    @patch("builtins.open", new_callable=mock_open, read_data="cpu0_thermal\n")
    def test_get_thermal_zones(self, mock_file, mock_listdir, mock_isdir):
        mock_isdir.return_value = True
        mock_listdir.return_value = ["thermal_zone0"]

        with patch("os.path.isfile") as mock_isfile:
            mock_isfile.return_value = True
            # First for type, second for temp
            mock_file.side_effect = [
                mock_open(read_data="cpu0_thermal").return_value,
                mock_open(read_data="45000").return_value,
            ]
            zones = get_thermal_zones()
            self.assertEqual(len(zones), 1)
            self.assertEqual(zones[0]["name"], "thermal_zone0")
            self.assertEqual(zones[0]["type"], "cpu0_thermal")
            self.assertEqual(zones[0]["display_name"], "CPU0 (Gold)")
            self.assertEqual(zones[0]["temp_millicelsius"], 45000)
            self.assertEqual(zones[0]["temp_celsius"], 45.0)
            self.assertFalse(zones[0]["warning"])

    @patch("os.path.isdir")
    @patch("os.listdir")
    def test_get_cpu_frequencies(self, mock_listdir, mock_isdir):
        mock_isdir.return_value = True
        mock_listdir.return_value = ["cpu0"]

        with patch("os.path.isfile") as mock_isfile, patch(
            "builtins.open"
        ) as mock_file:
            mock_isfile.return_value = True
            mock_file.side_effect = [
                mock_open(read_data="2000000").return_value,
                mock_open(read_data="schedutil").return_value,
            ]
            freqs = get_cpu_frequencies()
            self.assertEqual(len(freqs), 1)
            self.assertEqual(freqs[0]["cpu"], 0)
            self.assertEqual(freqs[0]["frequency_khz"], 2000000)
            self.assertEqual(freqs[0]["frequency_mhz"], 2000.0)
            self.assertEqual(freqs[0]["governor"], "schedutil")

    @patch("os.path.isdir")
    @patch("builtins.open")
    def test_get_cpu_scaling_available(self, mock_file, mock_isdir):
        mock_isdir.return_value = True
        mock_file.side_effect = [
            mock_open(read_data="performance powersave schedutil").return_value,
            mock_open(read_data="1000000").return_value,
            mock_open(read_data="2800000").return_value,
        ]
        with patch("os.path.isfile") as mock_isfile:
            mock_isfile.return_value = True
            res = get_cpu_scaling_available()
            self.assertEqual(
                res["governors"], ["performance", "powersave", "schedutil"]
            )
            self.assertEqual(res["min_freq"], 1000000)
            self.assertEqual(res["max_freq"], 2800000)

    @patch("builtins.open", new_callable=mock_open, read_data="3600.5 7200.0")
    def test_get_uptime(self, mock_file):
        uptime = get_uptime()
        self.assertEqual(uptime["seconds"], 3600.5)
        self.assertEqual(uptime["formatted"], "1h 0m")

    @patch("dashboard.services.battery.get_cpu_scaling_available")
    @patch("dashboard.services.battery.run_sudo_command")
    def test_set_cpu_governor(self, mock_run_sudo, mock_scaling):
        mock_scaling.return_value = {"governors": ["performance", "powersave"]}
        mock_run_sudo.return_value = (0, "success", "")

        res = set_cpu_governor("performance")
        self.assertTrue(res["success"])
        self.assertEqual(res["governor"], "performance")

        # Unsupported governor
        res_unsupported = set_cpu_governor("invalid_gov")
        self.assertFalse(res_unsupported["success"])


if __name__ == "__main__":
    unittest.main()
