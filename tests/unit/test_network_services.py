import json
import pytest
from unittest.mock import patch
from server.services.network import get_ip_addresses


class TestNetworkServicesTailscaleDeprioritization:
    """Test interface sorting and Tailscale deprioritization in network services."""

    def test_get_ip_addresses_deprioritizes_tailscale(self):
        """Test that get_ip_addresses sorts Tailscale lower than WiFi, Ethernet, etc."""
        raw_ip_json = json.dumps([
            {
                "ifname": "tailscale0",
                "link_type": "none",
                "operstate": "UP",
                "address": "00:00:00:00:00:00",
                "addr_info": [{"family": "inet", "local": "100.64.0.1", "prefixlen": 32, "scope": "global"}],
                "stats64": {"rx": {"bytes": 100}, "tx": {"bytes": 200}},
            },
            {
                "ifname": "wlan0",
                "link_type": "ether",
                "operstate": "UP",
                "address": "aa:bb:cc:dd:ee:01",
                "addr_info": [{"family": "inet", "local": "192.168.1.50", "prefixlen": 24, "scope": "global"}],
                "stats64": {"rx": {"bytes": 10000}, "tx": {"bytes": 20000}},
            },
            {
                "ifname": "eth0",
                "link_type": "ether",
                "operstate": "UP",
                "address": "aa:bb:cc:dd:ee:02",
                "addr_info": [{"family": "inet", "local": "10.0.0.5", "prefixlen": 24, "scope": "global"}],
                "stats64": {"rx": {"bytes": 5000}, "tx": {"bytes": 5000}},
            },
        ])

        with patch("server.services.network.get_gateways", return_value=[{"interface": "wlan0", "gateway": "192.168.1.1"}]):
            with patch("server.services.network.run_command", return_value=(0, raw_ip_json, "")):
                result = get_ip_addresses()
                names = [i["name"] for i in result]
                # wlan0 is default route (score 10)
                assert names[0] == "wlan0"
                # eth0 is ethernet up (score 25)
                assert names[1] == "eth0"
                # tailscale0 is deprioritized (score 80)
                assert names[2] == "tailscale0"
                # tailscale0 should be categorized as virtual
                tailscale_iface = next(i for i in result if i["name"] == "tailscale0")
                assert tailscale_iface["category"] == "virtual"
