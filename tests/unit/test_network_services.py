import unittest
from unittest.mock import patch, mock_open
from dashboard.services.network import (
    format_bytes,
    get_known_dns_provider,
    get_gateways,
    get_ip_addresses,
    get_wifi_info,
)


class TestNetworkServices(unittest.TestCase):
    def test_format_bytes(self):
        self.assertEqual(format_bytes(0), "0 B")
        self.assertEqual(format_bytes(500), "500 B")
        self.assertEqual(format_bytes(1024), "1.0 KB")
        self.assertEqual(format_bytes(1500), "1.5 KB")
        self.assertEqual(format_bytes(1024 * 1024), "1.0 MB")
        self.assertEqual(format_bytes(1024 * 1024 * 1024), "1.0 GB")
        self.assertEqual(format_bytes(1024 * 1024 * 1024 * 1024), "1.0 TB")
        self.assertEqual(format_bytes(1024 * 1024 * 1024 * 1024 * 1024), "1.0 PB")

    def test_get_known_dns_provider(self):
        self.assertEqual(get_known_dns_provider(""), "Unknown")
        self.assertEqual(get_known_dns_provider("127.0.0.1"), "Local Stub Resolver")
        self.assertEqual(get_known_dns_provider("1.1.1.1"), "Cloudflare DNS")
        self.assertEqual(get_known_dns_provider("8.8.8.8"), "Google Public DNS")
        self.assertEqual(get_known_dns_provider("9.9.9.9"), "Quad9")
        self.assertEqual(get_known_dns_provider("208.67.222.222"), "OpenDNS")
        self.assertEqual(get_known_dns_provider("94.140.14.14"), "AdGuard DNS")
        self.assertEqual(
            get_known_dns_provider("192.168.1.1"), "Local Router / Gateway"
        )
        self.assertEqual(get_known_dns_provider("10.0.0.1"), "Local Router / Gateway")
        self.assertEqual(get_known_dns_provider("172.16.0.1"), "Local Router / Gateway")
        self.assertEqual(
            get_known_dns_provider("172.31.255.255"), "Local Router / Gateway"
        )
        self.assertEqual(get_known_dns_provider("203.0.113.1"), "ISP / Custom DNS")

    @patch("dashboard.services.network.run_command")
    def test_get_gateways(self, mock_run_command):
        # Test with JSON output
        mock_run_command.return_value = (
            0,
            (
                '[{"gateway": "192.168.1.1", "dev": "eth0", '
                '"protocol": "dhcp", "metric": 100}]'
            ),
            "",
        )
        gateways = get_gateways()
        self.assertEqual(len(gateways), 1)
        self.assertEqual(gateways[0]["gateway"], "192.168.1.1")
        self.assertEqual(gateways[0]["interface"], "eth0")

        # Test with text output
        mock_run_command.return_value = (0, "default via 192.168.1.1 dev eth0", "")
        gateways = get_gateways()
        self.assertEqual(len(gateways), 1)
        self.assertEqual(gateways[0]["gateway"], "192.168.1.1")
        self.assertEqual(gateways[0]["interface"], "eth0")

        # Test with no output
        mock_run_command.return_value = (1, "", "")
        gateways = get_gateways()
        self.assertEqual(len(gateways), 0)

    @patch("dashboard.services.network.run_command")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="1500")
    def test_get_ip_addresses(self, mock_open, mock_exists, mock_run_command):
        # Setup mocks
        mock_exists.return_value = True
        mock_run_command.return_value = (
            0,
            (
                '[\n{\n"ifname": "eth0",\n"address": "00:1a:2b:3c:4d:5e",\n'
                '"mtu": 1500,\n"flags": ["UP", "LOWER_UP"],\n'
                '"operstate": "UP",\n"addr_info": [\n{\n'
                '"local": "192.168.1.100",\n"prefixlen": 24,\n'
                '"family": "inet",\n"scope": "global"\n}\n]\n}\n]'
            ),
            "",
        )

        # Test with JSON output
        interfaces = get_ip_addresses()
        self.assertEqual(len(interfaces), 1)
        self.assertEqual(interfaces[0]["name"], "eth0")
        self.assertEqual(interfaces[0]["mac"], "00:1a:2b:3c:4d:5e")
        self.assertEqual(interfaces[0]["mtu"], 1500)
        self.assertEqual(interfaces[0]["state"], "UP")
        self.assertEqual(len(interfaces[0]["ipv4"]), 1)
        self.assertEqual(interfaces[0]["ipv4"][0]["address"], "192.168.1.100")

        # Test interface prioritization
        interfaces[0]["name"] = "tailscale0"
        interfaces.append(
            {
                "name": "wlan0",
                "category": "wireless",
                "is_up": True,
                "is_default": False,
            }
        )
        interfaces.append(
            {
                "name": "eth1",
                "category": "ethernet",
                "is_up": True,
                "is_default": False,
            }
        )
        interfaces.append(
            {
                "name": "eth0",
                "category": "ethernet",
                "is_up": True,
                "is_default": True,
            }
        )

        # Sort interfaces
        interfaces.sort(
            key=lambda x: (
                (
                    80
                    if x["name"].startswith("tailscale")
                    else (
                        10
                        if x.get("is_default")
                        else (
                            20
                            if x.get("category") == "wireless"
                            else (
                                25
                                if x.get("category") == "ethernet" and x.get("is_up")
                                else (30 if x.get("category") == "ethernet" else 100)
                            )
                        )
                    )
                ),
                x["name"],
            )
        )

        # Verify prioritization
        self.assertEqual(interfaces[0]["name"], "eth0")  # Default interface
        self.assertEqual(interfaces[1]["name"], "wlan0")  # Wireless
        self.assertEqual(interfaces[2]["name"], "eth1")  # Ethernet
        self.assertEqual(interfaces[3]["name"], "tailscale0")  # Tailscale

    @patch("dashboard.services.network.which")
    @patch("dashboard.services.network.run_command")
    @patch("os.path.exists")
    def test_get_wifi_info(self, mock_exists, mock_run_command, mock_which):
        # Test with nmcli output
        mock_exists.return_value = True
        mock_which.return_value = True
        mock_run_command.return_value = (
            0,
            "yes:MyWiFi:00\\:1a\\:2b\\:3c\\:4d\\:5e:Infra:6:2437:54:80:WPA2",
            "",
        )
        wifi_info = get_wifi_info()
        self.assertTrue(wifi_info["has_hardware"])
        self.assertTrue(wifi_info["connected"])
        self.assertEqual(wifi_info["ssid"], "MyWiFi")
        self.assertEqual(wifi_info["bssid"], "00:1a:2b:3c:4d:5e")
        self.assertEqual(wifi_info["channel"], "6")
        self.assertEqual(wifi_info["frequency"], "2437")
        self.assertEqual(wifi_info["signal_percent"], 80)
        self.assertEqual(wifi_info["security"], "WPA2")
        self.assertEqual(wifi_info["mode"], "Infra")
        self.assertEqual(wifi_info["source"], "nmcli")

        # Test with iwconfig output
        mock_run_command.return_value = (
            0,
            (
                'wlan0     IEEE 802.11  ESSID:"MyWiFi"  Nickname:""\n'
                "          Mode:Managed  Frequency:2.437 GHz  "
                "Access Point: 00:1A:2B:3C:4D:5E\n"
                "          Bit Rate=54 Mb/s   Tx-Power=20 dBm\n"
                "          Retry short limit:7   RTS thr:off   "
                "Fragment thr:off\n"
                "          Power Management:on\n"
                "          Link Quality=80/100  Signal level=-40 dBm\n"
                "          Rx invalid nwid:0  Rx invalid crypt:0  "
                "Rx invalid frag:0\n"
                "          Tx excessive retries:0  Invalid misc:0   "
                "Missed beacon:0"
            ),
            "",
        )
        wifi_info = get_wifi_info()
        self.assertTrue(wifi_info["has_hardware"])
        self.assertTrue(wifi_info["connected"])
        self.assertEqual(wifi_info["ssid"], "MyWiFi")
        self.assertEqual(wifi_info["bssid"], "00:1A:2B:3C:4D:5E")
        self.assertEqual(wifi_info["bitrate"], "54 Mb/s")
        self.assertEqual(wifi_info["tx_power"], "20 dBm")
        self.assertEqual(wifi_info["signal_dbm"], "-40 dBm")
        self.assertEqual(wifi_info["signal_percent"], 80)
        self.assertEqual(wifi_info["source"], "iwconfig")

        # Test with no hardware
        mock_exists.return_value = False
        wifi_info = get_wifi_info()
        self.assertFalse(wifi_info["has_hardware"])
        self.assertFalse(wifi_info["connected"])
        self.assertEqual(
            wifi_info["message"],
            "No wireless network interfaces detected on this device.",
        )


if __name__ == "__main__":
    unittest.main()
