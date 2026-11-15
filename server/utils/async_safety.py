"""Async safety utilities and runtime event loop execution guards."""

import asyncio


def assert_not_in_running_loop(func_name: str) -> None:
    """Ensure synchronous blocking code is not called directly on an active event loop.

    Args:
        func_name: Name of the synchronous function being guarded.

    Raises:
        RuntimeError: If called while an event loop is active on the current thread.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return
    raise RuntimeError(
        f"{func_name} is a blocking synchronous function and must not "
        "be called directly on the event loop. Use asyncio.to_thread instead."
    )
