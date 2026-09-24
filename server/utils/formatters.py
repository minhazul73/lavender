"""
Formatting helpers for bytes, percentages, and uptimes.
"""


def format_bytes(b: int | float) -> str:
    """Format byte count to human-readable string (e.g. 1.25 GB)."""
    if b < 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    value = float(b)
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024.0
    return f"{value:.1f} PB"


def format_uptime(seconds: float | int) -> str:
    """Format seconds into days, hours, minutes format."""
    total_sec = int(seconds)
    days = total_sec // 86400
    hours = (total_sec % 86400) // 3600
    minutes = (total_sec % 3600) // 60
    secs = total_sec % 60

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or hours > 0 or days > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def format_percent(val: float | int) -> str:
    """Format a float or int as percentage string."""
    return f"{float(val):.1f}%"
