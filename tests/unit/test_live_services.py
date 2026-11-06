import pytest

from server.services.collectors.battery import BatteryCollector
from server.services.collectors.cpu import CPUFreqCollector
from server.services.collectors.ram import RAMCollector
from server.services.collectors.thermal import ThermalCollector
from server.services.live import LiveMonitor, NetworkRateCollector
from server.services.live_buffer import MetricCollector
from server.services.live_monitor import get_live_monitor


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


class TestLiveMonitorOrchestration:
    """Test the LiveMonitor service orchestrates all collectors correctly."""

    @pytest.mark.asyncio
    async def test_get_all_metrics_assembles_all_collectors(self, monkeypatch):
        """get_all_metrics returns one key per collector with its payload."""
        monitor = LiveMonitor()

        cpu_payload = {"count": 4, "cpus": [], "primary_frequency_mhz": 1.8}
        ram_payload = {"total": 1000, "used": 500, "used_pct": 50.0}
        thermal_payload = [{"name": "zone0", "temp_celsius": 45.0}]
        battery_payload = {"percentage": 80, "state": "discharging"}
        network_payload = {"iface": "wlan0", "rx_bytes": 10, "tx_bytes": 20}

        async def fake_cpu(self):
            return cpu_payload

        async def fake_ram(self):
            return ram_payload

        async def fake_thermal(self):
            return thermal_payload

        async def fake_battery(self):
            return battery_payload

        async def fake_network(self):
            return network_payload

        monkeypatch.setattr(CPUFreqCollector, "collect", fake_cpu)
        monkeypatch.setattr(RAMCollector, "collect", fake_ram)
        monkeypatch.setattr(ThermalCollector, "collect", fake_thermal)
        monkeypatch.setattr(BatteryCollector, "collect", fake_battery)
        monkeypatch.setattr(NetworkRateCollector, "collect", fake_network)

        result = await monitor.get_all_metrics()
        assert result == {
            "cpu": cpu_payload,
            "ram": ram_payload,
            "thermal": thermal_payload,
            "battery": battery_payload,
            "network": network_payload,
        }

    @pytest.mark.asyncio
    async def test_get_all_metrics_returns_expected_top_level_keys(self, monkeypatch):
        """get_all_metrics exposes exactly the five metric domains."""
        monitor = LiveMonitor()

        async def fake_cpu(self):
            return {}

        async def fake_ram(self):
            return {}

        async def fake_thermal(self):
            return []

        async def fake_battery(self):
            return {}

        async def fake_network(self):
            return {}

        monkeypatch.setattr(CPUFreqCollector, "collect", fake_cpu)
        monkeypatch.setattr(RAMCollector, "collect", fake_ram)
        monkeypatch.setattr(ThermalCollector, "collect", fake_thermal)
        monkeypatch.setattr(BatteryCollector, "collect", fake_battery)
        monkeypatch.setattr(NetworkRateCollector, "collect", fake_network)

        result = await monitor.get_all_metrics()
        assert set(result.keys()) == {"cpu", "ram", "thermal", "battery", "network"}

    @pytest.mark.asyncio
    async def test_individual_metric_accessors(self, monkeypatch):
        """Each get_* accessor delegates to the matching collector."""
        monitor = LiveMonitor()

        async def fake_cpu(self):
            return {"domain": "cpu"}

        async def fake_ram(self):
            return {"domain": "ram"}

        async def fake_thermal(self):
            return [{"domain": "thermal"}]

        async def fake_battery(self):
            return {"domain": "battery"}

        async def fake_network(self):
            return {"domain": "network"}

        monkeypatch.setattr(CPUFreqCollector, "collect", fake_cpu)
        monkeypatch.setattr(RAMCollector, "collect", fake_ram)
        monkeypatch.setattr(ThermalCollector, "collect", fake_thermal)
        monkeypatch.setattr(BatteryCollector, "collect", fake_battery)
        monkeypatch.setattr(NetworkRateCollector, "collect", fake_network)

        assert await monitor.get_cpu() == {"domain": "cpu"}
        assert await monitor.get_ram() == {"domain": "ram"}
        assert await monitor.get_thermal() == [{"domain": "thermal"}]
        assert await monitor.get_battery() == {"domain": "battery"}
        assert await monitor.get_network() == {"domain": "network"}

    @pytest.mark.asyncio
    async def test_add_client_starts_collectors_on_first_connect(self, monkeypatch):
        """The first client triggers lazy start of every collector."""
        monitor = LiveMonitor()
        started: list[str] = []

        def fake_start(self, loop):
            started.append(self._buffer_key)

        monkeypatch.setattr(MetricCollector, "start", fake_start)

        await monitor.add_client()
        assert monitor._client_count == 1
        assert monitor._started is True
        assert set(started) == {"cpu", "ram", "thermal", "battery", "network"}

    @pytest.mark.asyncio
    async def test_remove_client_stops_collectors_when_last_disconnects(self, monkeypatch):
        """Collectors keep running while clients remain and stop at zero."""
        monitor = LiveMonitor()
        started: list[str] = []
        stopped: list[str] = []

        def fake_start(self, loop):
            started.append(self._buffer_key)

        def fake_stop(self):
            stopped.append(self._buffer_key)

        monkeypatch.setattr(MetricCollector, "start", fake_start)
        monkeypatch.setattr(MetricCollector, "stop", fake_stop)

        await monitor.add_client()
        await monitor.add_client()  # 2 clients
        assert monitor._client_count == 2
        assert monitor._started is True

        await monitor.remove_client()  # 1 client -> still running
        assert monitor._client_count == 1
        assert monitor._started is True
        assert stopped == []

        await monitor.remove_client()  # 0 clients -> stop all
        assert monitor._client_count == 0
        assert monitor._started is False
        assert set(stopped) == {"cpu", "ram", "thermal", "battery", "network"}

    @pytest.mark.asyncio
    async def test_remove_client_never_goes_negative(self, monkeypatch):
        """Removing clients below zero is a no-op and never starts/stops."""
        monitor = LiveMonitor()
        started: list[str] = []

        def fake_start(self, loop):
            started.append(self._buffer_key)

        monkeypatch.setattr(MetricCollector, "start", fake_start)

        await monitor.remove_client()  # no clients to begin with
        assert monitor._client_count == 0
        assert monitor._started is False
        assert started == []

    def test_get_live_monitor_returns_singleton(self, monkeypatch):
        """get_live_monitor returns the same instance across calls."""
        import server.services.live_monitor as lm

        monkeypatch.setattr(lm, "_live_monitor", None)
        m1 = get_live_monitor()
        m2 = get_live_monitor()
        assert m1 is m2
        assert isinstance(m1, LiveMonitor)

    def test_monitor_exposes_collector_properties(self):
        """The public properties return the underlying collector instances."""
        monitor = LiveMonitor()
        assert isinstance(monitor.cpu, CPUFreqCollector)
        assert isinstance(monitor.ram, RAMCollector)
        assert isinstance(monitor.thermal, ThermalCollector)
        assert isinstance(monitor.battery, BatteryCollector)
        assert isinstance(monitor.network, NetworkRateCollector)
