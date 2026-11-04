"""Live telemetry collector."""

from server.services.live import LiveMonitor, get_live_monitor as _get_live_monitor

__all__ = ["get_live_monitor"]


def get_live_monitor() -> LiveMonitor:
    """Get the live monitor instance."""
    return _get_live_monitor()