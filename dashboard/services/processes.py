"""
Process and resource management.
"""
import subprocess
import os
import time
from datetime import datetime

from dashboard.dependencies import run_command, run_sudo_command


def get_top_processes(sort_by: str = "mem", limit: int = 20) -> list[dict]:
    """
    Get top processes by CPU or memory usage.
    BusyBox ps aux only gives: PID USER TIME COMMAND (4 columns).
    No %CPU/%MEM/VSZ/RSS — we sort by TIME as a proxy.
    For memory, read /proc/PID/stat for RSS.
    """
    code, out, err = run_command(["ps", "aux"], timeout=10)
    if code != 0:
        return [{"error": err}]

    processes = []
    lines = out.split("\n")
    # Skip header: PID USER TIME COMMAND
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 3)  # PID USER TIME COMMAND (4 fields)
        if len(parts) >= 4:
            try:
                pid = int(parts[0])
                user = parts[1]
                time_str = parts[2]
                command = parts[3]
                # Parse TIME: MM:SS or HH:MM:SS — convert to seconds
                time_secs = 0
                for part in time_str.split(":"):
                    time_secs = time_secs * 60 + int(part)
                # Get RSS from /proc/PID/stat (field 24, in pages)
                rss_kb = 0
                try:
                    with open(f"/proc/{pid}/stat", "r") as f:
                        stat = f.read().split()
                        # rss is field 24 (0-indexed: 23), in pages
                        rss_pages = int(stat[23])
                        # page size from /proc/sysinfo or assume 4096
                        rss_kb = rss_pages * 4
                except Exception:
                    pass
                processes.append({
                    "user": user,
                    "pid": pid,
                    "cpu": time_secs,       # TIME in seconds as CPU proxy
                    "mem": rss_kb,          # RSS in KB from /proc/PID/stat
                    "time": time_str,
                    "command": command,
                    "vsz": 0,              # Not available from BusyBox ps
                    "rss": rss_kb,          # RSS in KB
                    "stat": "?",           # Not available from BusyBox ps
                    "start": "?",          # Not available from BusyBox ps
                })
            except (ValueError, IndexError):
                continue

    # Sort: by TIME (cpu proxy) or RSS (mem)
    if sort_by == "cpu":
        processes.sort(key=lambda p: p["cpu"], reverse=True)
    else:
        processes.sort(key=lambda p: p["mem"], reverse=True)
    return processes[:limit]


def get_system_load() -> dict:
    """Get system load averages and uptime."""
    try:
        with open("/proc/loadavg", "r") as f:
            parts = f.read().strip().split()
            load_avg = {
                "1min": float(parts[0]),
                "5min": float(parts[1]),
                "15min": float(parts[2]),
                "running": parts[3].split("/")[0],
                "total": parts[3].split("/")[1],
            }
    except Exception:
        load_avg = {"error": "Cannot read /proc/loadavg"}

    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.read().strip().split()[0])
            load_avg["uptime_seconds"] = uptime_seconds
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            load_avg["uptime_formatted"] = f"{days}d {hours}h {minutes}m"
    except Exception:
        load_avg["uptime_formatted"] = "Unknown"

    return load_avg


def kill_process(pid: int, signal: int = 9) -> dict:
    """Kill a process by PID (requires sudo for many processes)."""
    code, out, err = run_sudo_command(["kill", f"-{signal}", str(pid)], timeout=10)
    return {
        "success": code == 0,
        "pid": pid,
        "signal": signal,
        "output": out,
        "error": err,
    }


def get_memory_info() -> dict:
    """Get detailed memory information from /proc/meminfo."""
    info = {}
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.strip().split(": ")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip()
                    if val.endswith(" kB"):
                        val = val[:-3]
                    info[key] = val
    except Exception:
        info["error"] = "Cannot read /proc/meminfo"
    return info


def get_memory_human() -> dict:
    """Get memory info in human-readable format using free -h style."""
    code, out, err = run_command(["free", "-h"], timeout=5)
    result = {"raw": out, "error": err, "parsed": {}}
    if code == 0:
        lines = out.split("\n")
        if len(lines) >= 2:
            mem_parts = lines[1].split()
            if len(mem_parts) >= 4:
                result["parsed"] = {
                    "total": mem_parts[1],
                    "used": mem_parts[2],
                    "free": mem_parts[3],
                    "shared": mem_parts[4] if len(mem_parts) > 4 else "0",
                }
            if len(lines) >= 3:
                swap_parts = lines[2].split()
                if len(swap_parts) >= 4:
                    result["parsed"]["swap_total"] = swap_parts[1]
                    result["parsed"]["swap_used"] = swap_parts[2]
                    result["parsed"]["swap_free"] = swap_parts[3]
    return result
