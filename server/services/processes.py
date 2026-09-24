"""
Process and resource management.
"""
import subprocess
import os
import time
from datetime import datetime

from dashboard.dependencies import run_command, run_sudo_command


def get_top_processes(sort_by: str = "mem", limit: int = 0) -> list[dict]:
    """
    Get processes by CPU or memory usage.
    Supports both standard procps ps aux (11 columns) and BusyBox ps aux (4 columns).
    If limit <= 0, returns all processes.
    """
    code, out, err = run_command(["ps", "aux"], timeout=10)
    if code != 0:
        return [{"error": err}]

    total_mem_kb = 0
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    total_mem_kb = float(line.split()[1])
                    break
    except Exception:
        pass

    processes = []
    lines = out.strip().split("\n")
    if not lines:
        return []

    header = lines[0].split()
    is_busybox = len(header) >= 1 and header[0] == "PID"

    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        try:
            if is_busybox:
                # BusyBox format: PID USER TIME COMMAND
                parts = line.split(None, 3)
                if len(parts) < 4:
                    continue
                pid = int(parts[0])
                user = parts[1]
                time_str = parts[2]
                command = parts[3]

                time_secs = 0
                for part in time_str.split(":"):
                    time_secs = time_secs * 60 + int(part)

                state = "S"
                rss_kb = 0
                vsz_kb = 0
                try:
                    with open(f"/proc/{pid}/stat", "r") as f:
                        content = f.read()
                        rparen = content.rfind(")")
                        if rparen != -1:
                            rest = content[rparen + 2:].split()
                            state = rest[0]
                            vsz_kb = int(rest[20]) // 1024
                            rss_kb = int(rest[21]) * 4
                except Exception:
                    pass

                mem_pct = round((rss_kb / total_mem_kb) * 100, 1) if total_mem_kb > 0 else 0.0

                processes.append({
                    "pid": pid,
                    "user": user,
                    "cpu": 0.0,
                    "cpu_time": time_secs,
                    "time": time_str,
                    "mem": rss_kb,
                    "mem_pct": mem_pct,
                    "vsz": vsz_kb,
                    "rss": rss_kb,
                    "stat": state,
                    "command": command,
                })
            else:
                # Procps format: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
                parts = line.split(None, 10)
                if len(parts) < 11:
                    continue
                user = parts[0]
                pid = int(parts[1])
                cpu_pct = float(parts[2])
                mem_pct = float(parts[3])
                vsz_kb = int(parts[4])
                rss_kb = int(parts[5])
                stat = parts[7]
                time_str = parts[9]
                command = parts[10]

                time_secs = 0
                for part in time_str.split(":"):
                    try:
                        time_secs = time_secs * 60 + int(part)
                    except ValueError:
                        pass

                processes.append({
                    "pid": pid,
                    "user": user,
                    "cpu": cpu_pct,
                    "cpu_time": time_secs,
                    "time": time_str,
                    "mem": rss_kb,
                    "mem_pct": mem_pct,
                    "vsz": vsz_kb,
                    "rss": rss_kb,
                    "stat": stat,
                    "command": command,
                })
        except (ValueError, IndexError):
            continue

    if sort_by == "cpu":
        processes.sort(key=lambda p: (p.get("cpu", 0), p.get("cpu_time", 0)), reverse=True)
    elif sort_by == "pid":
        processes.sort(key=lambda p: p.get("pid", 0))
    elif sort_by == "user":
        processes.sort(key=lambda p: p.get("user", ""))
    elif sort_by == "name":
        processes.sort(key=lambda p: p.get("command", "").lower())
    else:  # default 'mem'
        processes.sort(key=lambda p: p.get("mem", 0), reverse=True)

    if limit > 0:
        return processes[:limit]
    return processes


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

    # Add calculated memory percentage from /proc/meminfo
    try:
        with open("/proc/meminfo", "r") as f:
            meminfo = {}
            for line in f:
                p = line.split(":")
                if len(p) == 2:
                    meminfo[p[0].strip()] = float(p[1].split()[0])
            total = meminfo.get("MemTotal", 0)
            avail = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
            if total > 0:
                used = total - avail
                result["parsed"]["percent"] = round((used / total) * 100, 1)
    except Exception:
        pass

    return result
