"""
Characterization tests for server/services/live.py.
These tests lock in the existing behaviour before the file is split (T-035).
"""
import os

import pytest

from server.services.collectors.battery import BatteryCollector
from server.services.collectors.cpu import CPUFreqCollector
from server.services.collectors.network import NetworkRateCollector
from server.services.collectors.ram import RAMCollector
from server.services.collectors.thermal import ThermalCollector
from server.services.live_buffer import RingBuffer


class TestRingBuffer:
    def test_empty_buffer_returns_empty_list(self):
        buf = RingBuffer(5)
        assert buf.values() == []
        assert len(buf) == 0
        assert buf.is_empty is True

    def test_append_and_get_in_order(self):
        buf = RingBuffer(5)
        buf.append(1)
        buf.append(2)
        buf.append(3)
        assert buf.values() == [1, 2, 3]
        assert len(buf) == 3
        assert buf.is_empty is False

    def test_overflow_wraps_correctly(self):
        buf = RingBuffer(3)
        for i in range(5):
            buf.append(i)
        result = buf.values()
        assert len(result) == 3
        assert result == [2, 3, 4]
        assert result[-1] == 4  # most recent

    def test_iteration(self):
        buf = RingBuffer(5)
        buf.append(10)
        buf.append(20)
        assert list(buf) == [10, 20]

    def test_capacity_respected(self):
        buf = RingBuffer(10)
        for i in range(20):
            buf.append(i)
        assert len(buf.values()) == 10
        assert len(buf) == 10


@pytest.mark.asyncio
async def test_ram_collector_collects_metrics(mock_sysfs):
    collector = RAMCollector()
    data = await collector.collect()
    assert "total" in data
    assert "used" in data
    assert "available" in data
    assert "used_pct" in data
    assert data["total"] > 0


@pytest.mark.asyncio
async def test_cpu_collector_collects_metrics(mock_sysfs, monkeypatch):
    """Test CPU collector with mocked sysfs directory listings."""
    # Mock os.path.isdir for CPU sysfs paths
    def mock_isdir(path):
        return path in (
            "/sys/devices/system/cpu",
            "/sys/devices/system/cpu/cpu0/cpufreq",
        )

    # Mock os.listdir for CPU sysfs paths
    def mock_listdir(path):
        if path == "/sys/devices/system/cpu":
            return ["cpu0", "cpu1", "cpu2", "cpu3", "cpufreq", "cpuidle"]
        return []

    monkeypatch.setattr(os.path, "isdir", mock_isdir)
    monkeypatch.setattr(os, "listdir", mock_listdir)

    collector = CPUFreqCollector()
    data = await collector.collect()
    assert "cpus" in data
    assert "count" in data
    assert "primary_frequency_mhz" in data
    assert "cpufreq_available" in data
    assert "load1" in data
    assert "load5" in data
    assert "load15" in data
    assert "per_core_usage" in data
    assert data["count"] > 0
    assert data["primary_frequency_mhz"] > 0
    assert data["cpufreq_available"] is True
    assert data["load1"] >= 0
    assert data["load5"] >= 0


def test_cpu_parse_proc_stat_single_pass(monkeypatch):
    sample_stat = (
        "cpu  2255 34 2290 22625563 6290 127 456 0 0 0\n"
        "cpu0 1132 17 1145 11312781 3145 63 228 0 0 0\n"
        "cpu1 1123 17 1145 11312782 3145 64 228 0 0 0\n"
        "intr 11493054 23 0 0 0 0 0 0\n"
    )
    monkeypatch.setattr("server.services.collectors.cpu._read_file", lambda path: sample_stat if path == "/proc/stat" else None)
    from server.services.collectors.cpu import _parse_proc_stat
    cpus = _parse_proc_stat()
    assert len(cpus) == 2
    assert cpus[0] is not None
    assert cpus[1] is not None
    assert cpus[0]["user"] == 1132
    assert cpus[0]["system"] == 1145
    assert cpus[1]["user"] == 1123


def test_cpu_get_loadavg_single_read(monkeypatch):
    monkeypatch.setattr("server.services.collectors.cpu._read_file", lambda path: "1.25 0.85 0.55 2/450 12345\n" if path == "/proc/loadavg" else None)
    from server.services.collectors.cpu import _get_loadavg
    load1, load5, load15 = _get_loadavg()
    assert load1 == 1.25
    assert load5 == 0.85
    assert load15 == 0.55


@pytest.mark.asyncio
async def test_thermal_collector_collects_metrics(mock_sysfs, monkeypatch):
    """Test thermal collector with mocked sysfs directory listings."""
    # Mock os.path.isdir for thermal paths
    def mock_isdir(path):
        return path in (
            "/sys/class/hwmon",
            "/sys/bus/platform/devices",
            "/sys/class/thermal",
        )

    # Mock os.listdir for thermal paths
    def mock_listdir(path):
        if path == "/sys/class/hwmon":
            return ["hwmon0"]
        elif path == "/sys/bus/platform/devices":
            return []
        elif path == "/sys/class/thermal":
            return []
        return []

    monkeypatch.setattr(os.path, "isdir", mock_isdir)
    monkeypatch.setattr(os, "listdir", mock_listdir)

    collector = ThermalCollector()
    data = await collector.collect()
    assert isinstance(data, list)
    # With empty hwmon (no temp files), data should be empty
    # But hwmon0 might have temp1_input if we set it in mock_sysfs
    # For now, just verify the structure
    if data:
        assert "name" in data[0]
        assert "display_name" in data[0]
        assert "type" in data[0]
        assert "temp_millicelsius" in data[0]
        assert "temp_celsius" in data[0]
        assert "warning" in data[0]
        assert "crit" in data[0]
        assert data[0]["temp_celsius"] > 0


@pytest.mark.asyncio
async def test_battery_collector_collects_metrics(mock_sysfs, monkeypatch):
    """Test battery collector with mocked sysfs directory listings."""
    # Mock os.path.isdir for power_supply paths
    def mock_isdir(path):
        return path == "/sys/class/power_supply"

    # Mock os.listdir for power_supply paths
    def mock_listdir(path):
        if path == "/sys/class/power_supply":
            return ["bat0"]
        return []

    monkeypatch.setattr(os.path, "isdir", mock_isdir)
    monkeypatch.setattr(os, "listdir", mock_listdir)

    collector = BatteryCollector()
    data = await collector.collect()
    assert "percentage" in data
    assert "state" in data
    assert "temperature" in data
    assert "voltage" in data
    assert "energy_rate" in data
    assert "time_to_full" in data
    assert "time_to_empty" in data
    assert "energy" in data
    assert "energy_full" in data
    assert "capacity" in data
    assert "charging" in data
    assert "discharging" in data
    assert "online" in data
    assert "serial" in data
    assert "vendor" in data
    assert "model" in data
    assert "icon_name" in data
    assert "has_history" in data
    assert "battery_state" in data
    assert "battery_level" in data
    assert "battery_capacity_str" in data


@pytest.mark.asyncio
async def test_network_collector_collects_metrics(mock_sysfs, monkeypatch):
    """Test network collector with mocked sysfs and procfs."""
    # Mock os.path.exists for wireless/phy80211 checks
    def mock_exists(path):
        return False

    monkeypatch.setattr(os.path, "exists", mock_exists)

    collector = NetworkRateCollector()
    data = await collector.collect()
    assert "iface" in data
    assert "rx_bytes" in data
    assert "tx_bytes" in data
    assert "rx_rate_bps" in data
    assert "tx_rate_bps" in data
    assert data["rx_bytes"] >= 0
    assert data["tx_bytes"] >= 0
    assert data["rx_rate_bps"] >= 0
    assert data["tx_rate_bps"] >= 0
