"""Tests for LiveMonitor singleton lifecycle and multithreaded concurrency."""

import concurrent.futures
import threading

import server.services.live_monitor as lm
from server.services.live import LiveMonitor
from server.services.live_monitor import get_live_monitor


class InstrumentedLock:
    """Instruments Lock to observe acquisition attempts without changing locking semantics."""

    def __init__(self, real_lock: threading.Lock) -> None:
        self._real_lock = real_lock
        self.acquire_attempts = 0
        self._attempt_lock = threading.Lock()
        self.all_attempted = threading.Event()
        self._target_attempts = 0

    def set_target(self, target: int) -> None:
        with self._attempt_lock:
            self._target_attempts = target
            if self.acquire_attempts >= target:
                self.all_attempted.set()

    def acquire(self, *args, **kwargs) -> bool:
        with self._attempt_lock:
            self.acquire_attempts += 1
            if self._target_attempts and self.acquire_attempts >= self._target_attempts:
                self.all_attempted.set()
        return self._real_lock.acquire(*args, **kwargs)

    def release(self) -> None:
        self._real_lock.release()

    def __enter__(self) -> bool:
        return self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()


def test_get_live_monitor_returns_singleton(monkeypatch):
    """get_live_monitor returns the same instance across calls."""
    monkeypatch.setattr(lm, "_live_monitor", None)
    m1 = get_live_monitor()
    m2 = get_live_monitor()
    assert m1 is m2
    assert isinstance(m1, LiveMonitor)


def test_get_live_monitor_thread_safe_singleton(monkeypatch):
    """get_live_monitor safely returns single instance when initialized concurrently from multiple threads."""
    monkeypatch.setattr(lm, "_live_monitor", None)

    real_lock = lm._live_monitor_lock
    instrumented_lock = InstrumentedLock(real_lock)
    monkeypatch.setattr(lm, "_live_monitor_lock", instrumented_lock)

    orig_cls = lm.LiveMonitor
    construct_count = 0
    first_entered = threading.Event()
    release_event = threading.Event()

    class InstrumentedTestMonitor(orig_cls):
        def __init__(self, *args, **kwargs):
            nonlocal construct_count
            construct_count += 1
            if construct_count == 1:
                first_entered.set()
                if not release_event.wait(timeout=2.0):
                    raise TimeoutError("Timed out waiting for release_event in constructor")
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(lm, "LiveMonitor", InstrumentedTestMonitor)

    workers = 10
    instrumented_lock.set_target(workers)

    def worker(is_first: bool):
        if not is_first:
            if not first_entered.wait(timeout=2.0):
                raise TimeoutError("Timed out waiting for first constructor entry")
        return lm.get_live_monitor()

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        first_future = pool.submit(worker, True)
        assert first_entered.wait(timeout=2.0), "First worker failed to enter constructor"

        competing_futures = [pool.submit(worker, False) for _ in range(workers - 1)]

        # Prove competing callers have actively attempted to acquire the lock before releasing construction
        assert instrumented_lock.all_attempted.wait(timeout=2.0), (
            "Competing callers failed to contend for _live_monitor_lock"
        )
        release_event.set()

        results = [first_future.result(timeout=2.0)] + [
            f.result(timeout=2.0) for f in competing_futures
        ]

    assert construct_count == 1
    first = results[0]
    assert all(inst is first for inst in results)
    assert isinstance(first, orig_cls)
