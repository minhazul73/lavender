import unittest
from unittest.mock import patch, mock_open
from dashboard.services.device_info import (
    get_device_model,
    get_os_info,
    get_system_info,
)


class TestDeviceInfoServices(unittest.TestCase):
    @patch("os.path.exists")
    @patch("builtins.open")
    def test_get_device_model_dt(self, mock_file, mock_exists):
        mock_exists.side_effect = lambda p: p == "/sys/firmware/devicetree/base/model"
        mock_file.return_value = mock_open(
            read_data=b"Xiaomi Redmi Note 7\x00"
        ).return_value
        model = get_device_model()
        self.assertEqual(model, "Xiaomi Redmi Note 7")

    @patch("os.path.exists")
    @patch("builtins.open")
    def test_get_device_model_deviceinfo(self, mock_file, mock_exists):
        # Mock device tree not existing, but /etc/deviceinfo existing
        mock_exists.side_effect = lambda p: p == "/etc/deviceinfo"
        mock_file.return_value = mock_open(
            read_data='deviceinfo_name="Xiaomi Redmi Note 7"\n'
        ).return_value

        model = get_device_model()
        self.assertEqual(model, "Xiaomi Redmi Note 7")

    @patch("os.path.exists")
    @patch("builtins.open")
    def test_get_os_info(self, mock_file, mock_exists):
        mock_exists.side_effect = lambda p: p == "/etc/os-release"
        mock_file.return_value = mock_open(
            read_data=(
                'NAME="postmarketOS"\n'
                'PRETTY_NAME="postmarketOS v26.06"\n'
                'VERSION_ID="26.06"\n'
                'ID="postmarketos"\n'
            )
        ).return_value

        os_info = get_os_info()
        self.assertEqual(os_info["name"], "postmarketOS")
        self.assertEqual(os_info["pretty_name"], "postmarketOS v26.06")
        self.assertEqual(os_info["version"], "26.06")
        self.assertEqual(os_info["id"], "postmarketos")

    @patch("dashboard.services.device_info.get_device_model")
    @patch("dashboard.services.device_info.get_os_info")
    def test_get_system_info(self, mock_os_info, mock_device_model):
        mock_device_model.return_value = "Xiaomi Redmi Note 7"
        mock_os_info.return_value = {
            "name": "postmarketOS",
            "pretty_name": "postmarketOS v26.06",
            "version": "26.06",
            "id": "postmarketos",
        }

        # Clear lru_cache if any
        get_system_info.cache_clear()

        info = get_system_info()
        self.assertEqual(info["model"], "Xiaomi Redmi Note 7")
        self.assertEqual(info["os_name"], "postmarketOS")
        self.assertEqual(info["os_pretty"], "postmarketOS v26.06")
        self.assertEqual(info["os_version"], "26.06")
        self.assertEqual(info["os_id"], "postmarketos")


if __name__ == "__main__":
    unittest.main()
