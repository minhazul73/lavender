"""
Active sessions and login history parser.
"""
from server.core.executor import get_executor


def parse_active_sessions() -> list[dict]:
    """Parse active terminal and SSH sessions via who or loginctl."""
    sessions = []
    try:
        executor = get_executor()
        res = executor.run_sync(["who", "-u"], timeout=5)
        out = res.stdout.strip()
        if not out:
            # Fallback to plain who
            res = executor.run_sync(["who"], timeout=5)
            out = res.stdout.strip()

        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 4:
                user = parts[0]
                tty = parts[1]
                login_time = f"{parts[2]} {parts[3]}"
                host = parts[-1].strip("()") if "(" in parts[-1] else "Local"
                idle = parts[4] if len(parts) >= 6 and parts[4] != "." else "Active"
                sessions.append({
                    "user": user,
                    "tty": tty,
                    "host": host,
                    "login_time": login_time,
                    "idle": idle,
                })
    except Exception:
        pass
    return sessions


def parse_login_history(limit: int = 10) -> list[dict]:
    """Parse recent login history via last."""
    history = []
    try:
        executor = get_executor()
        res = executor.run_sync(["last", "-n", str(limit)], timeout=5)
        for line in res.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("wtmp begins") or line.startswith("reboot"):
                continue
            parts = line.split()
            if len(parts) >= 5:
                user = parts[0]
                tty = parts[1]
                host = parts[2]
                duration = " ".join(parts[3:])
                history.append({
                    "user": user,
                    "tty": tty,
                    "host": host,
                    "time": duration,
                })
    except Exception:
        pass
    return history
