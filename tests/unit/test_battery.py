import time
from unittest.mock import MagicMock, patch

import pytest

import server.services.battery as battery_svc


@pytest.fixture(autouse=True)
def clear_battery_cache():
    battery_svc._clear_battery_cache()
    try:
        yield
    finally:
        battery_svc._clear_battery_cache()


def test_battery_ttl_cache_avoids_repeated_subprocess():
    dummy_result = {"percentage": 75, "state": "discharging", "capacity": 98.0}
    with patch("server.services.battery._query_battery_info", return_value=dummy_result) as mock_query:
        first = battery_svc.get_battery_info()
        assert first["percentage"] == 75
        assert mock_query.call_count == 1

        # Second call within TTL should return cached result without calling query again
        second = battery_svc.get_battery_info()
        assert second["percentage"] == 75
        assert mock_query.call_count == 1

        # collect_upower should also share the cache
        third = battery_svc.collect_upower()
        assert third["percentage"] == 75
        assert mock_query.call_count == 1


def test_battery_ttl_cache_expires_after_5_seconds():
    start_time = 1000.0
    dummy_result_1 = {"percentage": 80, "state": "charging"}
    dummy_result_2 = {"percentage": 81, "state": "charging"}

    with patch("time.monotonic", return_value=start_time):
        with patch("server.services.battery._query_battery_info", return_value=dummy_result_1) as mock_query:
            res1 = battery_svc.get_battery_info()
            assert res1["percentage"] == 80
            assert mock_query.call_count == 1

    # 4.9 seconds later: still cached
    with patch("time.monotonic", return_value=start_time + 4.9):
        with patch("server.services.battery._query_battery_info", return_value=dummy_result_2) as mock_query:
            res2 = battery_svc.get_battery_info()
            assert res2["percentage"] == 80
            assert mock_query.call_count == 0

    # 5.1 seconds later: expired, queries again
    with patch("time.monotonic", return_value=start_time + 5.1):
        with patch("server.services.battery._query_battery_info", return_value=dummy_result_2) as mock_query:
            res3 = battery_svc.get_battery_info()
            assert res3["percentage"] == 81
            assert mock_query.call_count == 1


def test_battery_cache_defensive_copy():
    dummy_result = {"percentage": 90, "state": "charging"}
    with patch("server.services.battery._query_battery_info", return_value=dummy_result):
        res1 = battery_svc.get_battery_info()
        res1["percentage"] = 50  # mutate returned dict

        res2 = battery_svc.get_battery_info()
        assert res2["percentage"] == 90  # cache untouched


def test_get_upower_device_returns_none_on_missing():
    with patch("server.services.battery.run_command", return_value=(0, "line_power_AC\n", "")):
        device = battery_svc._get_upower_device()
        assert device is None

    with patch("server.services.battery.run_command", return_value=(1, "", "error")):
        device = battery_svc._get_upower_device()
        assert device is None


def test_get_upower_device_returns_path_when_present():
    with patch(
        "server.services.battery.run_command",
        return_value=(0, "/org/freedesktop/UPower/devices/line_power_AC\n/org/freedesktop/UPower/devices/battery_BAT0\n", "")
    ):
        device = battery_svc._get_upower_device()
        assert device == "/org/freedesktop/UPower/devices/battery_BAT0"


def test_collector_get_upower_device_returns_none_not_empty_string():
    from server.services.collectors.battery import BatteryCollector

    collector = BatteryCollector()
    with patch("subprocess.check_output", side_effect=Exception("not found")):
        device = collector._get_upower_device()
        assert device is None
        assert collector._upower_device is None
        # Second call returns cached None
        assert collector._get_upower_device() is None


def test_query_battery_info_comprehensive_fields():
    upower_raw = """
      native-path:          BAT0
      vendor:               SMP
      model:                L16M4PB1
      serial:               12345
      technology:           lithium-ion
      state:                discharging
      energy:               45.5 Wh
      energy-full:          50.0 Wh
      energy-full-design:   52.5 Wh
      energy-rate:          12.3 W
      voltage:              11.4 V
      voltage-min-design:   10.8 V
      voltage-max-design:   12.6 V
      time to empty:        3.7 hours
      time to full:         0 hours
      percentage:           91%
      capacity:             95.2%
      temperature:          26.5 degrees C
      charge-cycles:        42
      icon-name:            battery-full-symbolic
      continuation-key:
        line two
    """
    with patch("server.services.battery._get_upower_device", return_value="/dev/battery_test"):
        with patch("server.services.battery.run_command", return_value=(0, upower_raw, "")):
            info = battery_svc._query_battery_info()
            assert info["percentage"] == 91
            assert info["state"] == "discharging"
            assert info["voltage"] == 11.4
            assert info["voltage_min_design"] == 10.8
            assert info["voltage_max_design"] == 12.6
            assert info["time_to_empty"] == "3.7 hours"
            assert info["time_to_full"] == "0 hours"
            assert info["energy"] == 45.5
            assert info["energy_full"] == 50.0
            assert info["energy_full_design"] == 52.5
            assert info["energy_rate"] == 12.3
            assert info["capacity"] == 95.2
            assert info["temperature"] == 26.5
            assert info["charge_cycles"] == 42
            assert info["serial"] == "12345"
            assert info["vendor"] == "SMP"
            assert info["model"] == "L16M4PB1"
            assert info["technology"] == "lithium-ion"
            assert info["icon_name"] == "battery-full-symbolic"
            assert info["note"] == "Battery info"


def test_query_battery_info_command_failure():
    with patch("server.services.battery._get_upower_device", return_value=None):
        with patch("server.services.battery.run_command", return_value=(1, "", "Device not found")):
            res = battery_svc._query_battery_info()
            assert "error" in res
            assert res["note"] == "upower not available or battery not found"


def test_safe_converters_invalid_inputs():
    assert battery_svc._safe_float("invalid", "V") is None
    assert battery_svc._safe_int("invalid", "%") is None


