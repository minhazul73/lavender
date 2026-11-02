import pytest
from server.services.live import NetworkRateCollector


class TestNetworkRateCollectorPriority:
    """Test NetworkRateCollector interface selection and prioritization."""

    def test_primary_interface_prioritizes_wifi_ethernet_usb_over_tailscale(self, monkeypatch):
        """Test that WiFi, Ethernet, and USB interfaces are prioritized over Tailscale."""
        collector = NetworkRateCollector()

        monkeypatch.setattr(
            NetworkRateCollector,
            "_interface_operstate",
            staticmethod(lambda iface: "up" if iface in ("wlan0", "eth0", "usb0") else ("down" if iface == "enp0" else "unknown")),
        )
        monkeypatch.setattr(NetworkRateCollector, "_default_route_interface", staticmethod(lambda: "wlan0"))

        # Scenario 1: Tailscale vs WiFi (both have traffic)
        counters = {
            "tailscale0": (50000, 20000),
            "wlan0": (1000000, 500000),
            "lo": (10000, 10000),
        }
        assert collector._primary_interface(counters) == "wlan0"

        # Scenario 2: Tailscale vs USB tethering
        monkeypatch.setattr(NetworkRateCollector, "_default_route_interface", staticmethod(lambda: "usb0"))
        counters = {
            "tailscale0": (50000, 20000),
            "usb0": (800000, 400000),
        }
        assert collector._primary_interface(counters) == "usb0"

        # Scenario 3: Tailscale vs Ethernet
        monkeypatch.setattr(NetworkRateCollector, "_default_route_interface", staticmethod(lambda: "eth0"))
        counters = {
            "tailscale0": (50000, 20000),
            "eth0": (900000, 300000),
        }
        assert collector._primary_interface(counters) == "eth0"

        # Scenario 4: WiFi is up with 0 bytes, Tailscale has traffic -> WiFi still preferred
        monkeypatch.setattr(NetworkRateCollector, "_default_route_interface", staticmethod(lambda: "wlan0"))
        counters = {
            "tailscale0": (50000, 20000),
            "wlan0": (0, 0),
        }
        assert collector._primary_interface(counters) == "wlan0"

        # Scenario 5: Physical interfaces are down with 0 bytes, only Tailscale is active
        monkeypatch.setattr(NetworkRateCollector, "_default_route_interface", staticmethod(lambda: None))
        monkeypatch.setattr(
            NetworkRateCollector,
            "_interface_operstate",
            staticmethod(lambda iface: "down" if iface in ("wlan0", "usb0") else "unknown"),
        )
        counters = {
            "tailscale0": (50000, 20000),
            "wlan0": (0, 0),
            "usb0": (0, 0),
        }
        assert collector._primary_interface(counters) == "tailscale0"

    def test_interface_category_priority(self):
        """Test category priority ordering."""
        # WiFi
        assert NetworkRateCollector._interface_category_priority("wlan0") == 1
        assert NetworkRateCollector._interface_category_priority("wlp2s0") == 1
        # Ethernet
        assert NetworkRateCollector._interface_category_priority("eth0") == 2
        assert NetworkRateCollector._interface_category_priority("enp3s0") == 2
        # USB
        assert NetworkRateCollector._interface_category_priority("usb0") == 3
        assert NetworkRateCollector._interface_category_priority("rndis0") == 3
        # Cellular
        assert NetworkRateCollector._interface_category_priority("rmnet_data0") == 4
        # Tailscale / WireGuard
        assert NetworkRateCollector._interface_category_priority("tailscale0") == 8
        assert NetworkRateCollector._interface_category_priority("wg0") == 8
        # Other
        assert NetworkRateCollector._interface_category_priority("custom0") == 5

    def test_default_route_parsing(self, monkeypatch):
        """Test default route extraction from /proc/net/route format."""
        sample_route = (
            "Iface\tDestination\tGateway\tFlags\tRefCnt\tUse\tMetric\tMask\tMTU\tWindow\tIRTT\n"
            "tailscale0\t0044A8C0\t00000000\t0001\t0\t0\t0\t00FCFFFF\t0\t0\t0\n"
            "wlan0\t00000000\t0144A8C0\t0003\t0\t0\t600\t00000000\t0\t0\t0\n"
        )
        monkeypatch.setattr("server.services.live._read_file", lambda path: sample_route if path == "/proc/net/route" else None)
        assert NetworkRateCollector._default_route_interface() == "wlan0"
