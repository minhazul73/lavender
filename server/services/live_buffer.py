"""
RingBuffer and base metric collector infrastructure for live telemetry.
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from typing import List, Optional


class RingBuffer:
    """Fixed-size circular buffer for a single metric stream.

    Reads are lock-free (only append from one asyncio task, read from any).
    We don't need a lock because appends only happen in the collector loop
    which is single-threaded per metric; reads happen on main thread during
    HTTP response generation.
    """

    __slots__ = ("_buf", "_size")

    def __init__(self, size: int) -> None:
        self._buf: deque = deque(maxlen=size)
        self._size = size

    def __len__(self) -> int:
        return len(self._buf)

    def append(self, value: float) -> None:
        self._buf.append(value)

    def __iter__(self):
        return iter(self._buf)

    def values(self) -> List[float]:
        return list(self._buf)

    @property
    def is_empty(self) -> bool:
        return len(self._buf) == 0


@dataclass
class CollectorStats:
    """Running stats for a single collector."""
    sample_count: int = 0
    last_error: Optional[str] = None
    errors_in_row: int = 0


class MetricCollector:
    """Base class for a single-metric SSE collector.

    Subclasses implement:
      - collect() -> dict   (the current metric sample)
      - get_buffer()        (RingBuffer for sparkline/history)

    The base handles:
      - periodic collection loop
      - error backoff
      - buffer management
    """

    __slots__ = ("_interval_ms", "_buffer", "_stats", "_stop_event",
                 "_task", "_buffer_key")

    def __init__(self, interval_ms: int, history_size: int,
                 buffer_key: str) -> None:
        self._interval_ms = interval_ms
        self._buffer = RingBuffer(history_size)
        self._stats = CollectorStats()
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task[None]] = None
        self._buffer_key = buffer_key

    @property
    def buffer(self) -> RingBuffer:
        return self._buffer

    @property
    def stats(self) -> CollectorStats:
        return self._stats

    async def collect(self) -> dict:
        raise NotImplementedError

    async def _run_loop(self) -> None:
        """Main collection loop. Sleep-based, not fixed-schedule."""
        interval_s = self._interval_ms / 1000.0
        while not self._stop_event.is_set():
            try:
                sample = await self.collect()
                self._on_sample(sample)
                self._stats.errors_in_row = 0
                self._stats.last_error = None
            except Exception as exc:
                self._stats.errors_in_row += 1
                self._stats.last_error = str(exc)
                # Don't crash the whole SSE engine on a single collector
                # failure — log and continue after a brief pause.
                await asyncio.sleep(min(interval_s, 1.0))
            await asyncio.sleep(interval_s)

    def _on_sample(self, sample: dict) -> None:
        """Called for each successful sample. Subclasses may override."""
        pass

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        if self._task is not None and not self._task.done():
            return  # already running
        self._stop_event.clear()
        self._task = loop.create_task(self._run_loop(), name=f"collector-{self._buffer_key}")

    def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            try:
                self._task.cancel()
            except RuntimeError:
                pass
            self._task = None
