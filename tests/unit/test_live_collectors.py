"""
Characterization tests for server/services/live.py.
These tests lock in the existing behaviour before the file is split (T-035).
"""
import pytest
from server.services.live import RingBuffer, RAMCollector


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
