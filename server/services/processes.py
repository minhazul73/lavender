"""
Process and resource management.
"""

import heapq
import os

from server.core.executor import get_executor


def run_command(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Execute command via system executor synchronously."""
    res = get_executor().run_sync(cmd, timeout=float(timeout))
    return res.returncode, res.stdout, res.stderr


def run_sudo_command(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Execute privileged sudo command via system executor synchronously."""
    full_cmd = ["sudo"] + cmd if cmd and cmd[0] == "-n" else ["sudo", "-n"] + cmd
    return run_command(full_cmd, timeout)


def _parse_time_str(time_str: str) -> int:
    """Parse CPU time string into total seconds supporting colon, day prefix, and unit notation."""
    time_str = time_str.strip()
    if not time_str:
        return 0
    try:
        if "d" in time_str:
            d_str, rem = time_str.split("d", 1)
            h_val = int(rem.rstrip("h")) if rem.rstrip("h") else 0
            return int(d_str) * 86400 + h_val * 3600
        if "h" in time_str:
            h_str, rem = time_str.split("h", 1)
            m_val = int(rem.rstrip("m")) if rem.rstrip("m") else 0
            return int(h_str) * 3600 + m_val * 60
        days = 0
        if "-" in time_str:
            day_part, time_str = time_str.split("-", 1)
            days = int(day_part)
        time_secs = 0
        for part in time_str.split(":"):
            time_secs = time_secs * 60 + int(part)
        return days * 86400 + time_secs
    except (ValueError, IndexError):
        return 0


def _read_proc_stat(pid: int) -> tuple[str, int, int, int, str]:
    """Read process execution metrics from /proc/<pid>/stat."""
    state, vsz_kb, rss_kb, time_secs, time_str = "S", 0, 0, 0, "0:00"
    try:
        with open(f"/proc/{pid}/stat") as f:
            content = f.read()
        rparen = content.rfind(")")
        if rparen != -1:
            rest = content[rparen + 2:].split()
            state = rest[0]
            vsz_kb = int(rest[20]) // 1024
            page_kb = (os.sysconf("SC_PAGE_SIZE") // 1024) if hasattr(os, "sysconf") else 4
            rss_kb = int(rest[21]) * (page_kb or 4)
            clk = (os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100) or 100
            time_secs = (int(rest[11]) + int(rest[12])) // clk
            m, s = divmod(time_secs, 60)
            h, m = divmod(m, 60)
            time_str = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
    except Exception:
        pass
    return state, vsz_kb, rss_kb, time_secs, time_str


def _select_row_parser(header: list[str], total_mem_kb: float):
    """Select specialized row parser based on ps table header."""
    cols = [h.upper() for h in header]
    if cols and cols[0] != "PID":
        def parse_procps(line: str) -> dict | None:
            parts = line.split(None, 10)
            if len(parts) < 11:
                return None
            t_str = parts[9]
            return {
                "pid": int(parts[1]), "user": parts[0], "cpu": float(parts[2]),
                "cpu_time": _parse_time_str(t_str), "time": t_str,
                "mem": int(parts[5]), "mem_pct": float(parts[3]), "vsz": int(parts[4]),
                "rss": int(parts[5]), "stat": parts[7], "command": parts[10],
            }
        return parse_procps

    if "TIME" in cols:
        def parse_busybox_time(line: str) -> dict | None:
            parts = line.split(None, 3)
            if len(parts) < 4:
                return None
            pid, user, t_str, cmd = int(parts[0]), parts[1], parts[2], parts[3]
            st, vsz, rss, _, _ = _read_proc_stat(pid)
            pct = round((rss / total_mem_kb) * 100, 1) if total_mem_kb > 0 else 0.0
            return {
                "pid": pid, "user": user, "cpu": 0.0, "cpu_time": _parse_time_str(t_str),
                "time": t_str, "mem": rss, "mem_pct": pct, "vsz": vsz, "rss": rss,
                "stat": st, "command": cmd,
            }
        return parse_busybox_time

    cmd_idx = cols.index("COMMAND") if "COMMAND" in cols else len(cols) - 1
    stat_idx = cols.index("STAT") if "STAT" in cols else None
    vsz_idx = cols.index("VSZ") if "VSZ" in cols else None

    def parse_busybox_no_time(line: str) -> dict | None:
        parts = line.split(None, cmd_idx)
        if len(parts) < cmd_idx + 1:
            return None
        pid, user, cmd = int(parts[0]), parts[1], parts[cmd_idx]
        st = parts[stat_idx] if stat_idx is not None and len(parts) > stat_idx else None
        vsz = int(parts[vsz_idx]) if vsz_idx is not None and len(parts) > vsz_idx and parts[vsz_idx].isdigit() else 0
        p_st, p_vsz, rss, time_secs, time_str = _read_proc_stat(pid)
        pct = round((rss / total_mem_kb) * 100, 1) if total_mem_kb > 0 else 0.0
        return {
            "pid": pid, "user": user, "cpu": 0.0, "cpu_time": time_secs,
            "time": time_str, "mem": rss, "mem_pct": pct,
            "vsz": vsz or p_vsz, "rss": rss, "stat": st or p_st, "command": cmd,
        }
    return parse_busybox_no_time


def _parse_proc_line(line: str, is_busybox: bool, total_mem_kb: float) -> dict | None:
    """Parse single ps line with fallback header configuration."""
    hdr = ["PID", "USER", "TIME", "COMMAND"] if is_busybox else [
        "USER", "PID", "%CPU", "%MEM", "VSZ", "RSS", "TTY", "STAT", "START", "TIME", "COMMAND"
    ]
    try:
        return _select_row_parser(hdr, total_mem_kb)(line)
    except (ValueError, IndexError):
        return None


def get_top_processes(sort_by: str = "mem", limit: int = 0) -> list[dict]:
    """Get processes by CPU or memory usage with streaming/heap bounding."""
    code, out, err = run_command(["ps", "aux"], timeout=10)
    if code != 0:
        return [{"error": err}]

    total_mem_kb = 0
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    total_mem_kb = float(line.split()[1])
                    break
    except Exception:
        pass

    lines_iter = iter(out.splitlines())
    first_line = next(lines_iter, None)
    if not first_line:
        return []

    parse_row = _select_row_parser(first_line.split(), total_mem_kb)

    def _safe_parse(line: str):
        line = line.strip()
        if not line:
            return None
        try:
            return parse_row(line)
        except (ValueError, IndexError):
            return None

    proc_iter = (p for p in (_safe_parse(line) for line in lines_iter) if p is not None)

    sort_keys = {
        "cpu": (lambda p: (p.get("cpu", 0), p.get("cpu_time", 0)), True),
        "pid": (lambda p: p.get("pid", 0), False),
        "user": (lambda p: p.get("user", ""), False),
        "name": (lambda p: p.get("command", "").lower(), False),
        "mem": (lambda p: p.get("mem", 0), True),
    }
    key, reverse = sort_keys.get(sort_by, sort_keys["mem"])
    if limit > 0:
        return (heapq.nlargest if reverse else heapq.nsmallest)(limit, proc_iter, key=key)
    processes = list(proc_iter)
    processes.sort(key=key, reverse=reverse)
    return processes


def get_system_load() -> dict:
    """Get system load averages and uptime."""
    try:
        with open("/proc/loadavg") as f:
            p = f.read().strip().split()
            l1, l5, l15 = float(p[0]), float(p[1]), float(p[2])
            load_avg = {
                "1min": l1, "5min": l5, "15min": l15, "1m": l1, "5m": l5, "15m": l15,
                "load1": l1, "load5": l5, "load15": l15,
                "running": p[3].split("/")[0], "total": p[3].split("/")[1],
            }
    except Exception:
        load_avg = {"error": "Cannot read /proc/loadavg"}

    try:
        with open("/proc/uptime") as f:
            up = float(f.read().strip().split()[0])
            d, h, m = int(up // 86400), int((up % 86400) // 3600), int((up % 3600) // 60)
            load_avg.update({"uptime_seconds": up, "uptime_formatted": f"{d}d {h}h {m}m"})
    except Exception:
        load_avg["uptime_formatted"] = "Unknown"
    return load_avg


def kill_process(pid: int, signal: int = 9) -> dict:
    """Kill a process by PID (requires sudo for many processes)."""
    code, out, err = run_sudo_command(["kill", f"-{signal}", str(pid)], timeout=10)
    return {"success": code == 0, "pid": pid, "signal": signal, "output": out, "error": err}


def get_memory_info() -> dict:
    """Get detailed memory information from /proc/meminfo."""
    try:
        with open("/proc/meminfo") as f:
            return {
                p[0].strip(): p[1].strip()[:-3] if p[1].strip().endswith(" kB") else p[1].strip()
                for line in f if len(p := line.strip().split(": ")) == 2
            }
    except Exception:
        return {"error": "Cannot read /proc/meminfo"}


def get_memory_human() -> dict:
    """Get memory info in human-readable format using free -h style."""
    code, out, err = run_command(["free", "-h"], timeout=5)
    result = {"raw": out, "error": err, "parsed": {}}
    if code == 0:
        lines = out.split("\n")
        if len(lines) >= 2 and len(mem := lines[1].split()) >= 4:
            result["parsed"] = {
                "total": mem[1], "used": mem[2], "free": mem[3], "shared": mem[4] if len(mem) > 4 else "0",
            }
        if len(lines) >= 3 and len(swap := lines[2].split()) >= 4:
            result["parsed"].update({"swap_total": swap[1], "swap_used": swap[2], "swap_free": swap[3]})

    try:
        with open("/proc/meminfo") as f:
            meminfo = {p[0].strip(): float(p[1].split()[0]) for line in f if len(p := line.split(":")) == 2}
        total, avail = meminfo.get("MemTotal", 0), meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
        if total > 0:
            result["parsed"]["percent"] = round(((total - avail) / total) * 100, 1)
    except Exception:
        pass
    return result
