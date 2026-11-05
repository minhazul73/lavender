"""Live telemetry collector facade for backward compatibility.
"""

# Re-export the new LiveMonitor implementation that's split into a separate module.
# The wrapper keeps the original public API `get_live_monitor`.

from server.services.live_monitor import get_live_monitor

__all__ = ["get_live_monitor"]
