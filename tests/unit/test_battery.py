import time
from unittest.mock import MagicMock, patch

import pytest

import server.services.battery as battery_svc


def test_battery_ttl_cache_avoids_repeated_subprocess():
    battery_svc._clear_battery_cache()

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
    battery_svc._clear_battery_cache()

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
    battery_svc._clear_battery_cache()

    dummy_result = {"percentage": 90, "state": "charging"}
    with patch("server.services.battery._query_battery_info", return_value=dummy_result):
        res1 = battery_svc.get_battery_info()
        res1["percentage"] = 50  # mutate returned dict

        res2 = battery_svc.get_battery_info()
        assert res2["percentage"] == 90  # cache untouched
