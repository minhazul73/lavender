"""Tests for async safety helpers and event loop guards."""

import pytest

from server.utils.async_safety import assert_not_in_running_loop


def test_assert_not_in_running_loop_passes_outside_loop():
    """When no event loop is running on current thread, no exception is raised."""
    assert_not_in_running_loop("test_sync_fn")


@pytest.mark.asyncio
async def test_assert_not_in_running_loop_raises_in_loop():
    """When an event loop is running on current thread, raises descriptive RuntimeError."""
    with pytest.raises(RuntimeError) as exc_info:
        assert_not_in_running_loop("my_custom_func")

    msg = str(exc_info.value)
    assert "my_custom_func is a blocking synchronous function" in msg
    assert "must not be called directly on the event loop" in msg
    assert "Use asyncio.to_thread instead" in msg


@pytest.mark.asyncio
async def test_get_battery_info_raises_on_event_loop():
    """Verify get_battery_info invokes assert_not_in_running_loop."""
    from server.services.battery import get_battery_info

    with pytest.raises(RuntimeError) as exc_info:
        get_battery_info()

    assert "get_battery_info is a blocking synchronous function" in str(exc_info.value)
