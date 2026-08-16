"""
Hermes gateway and dashboard service controls.
"""
import subprocess
import os
import sqlite3
import json

from dashboard.dependencies import run_command, run_sudo_command, get_hermes_version, get_hermes_skills


def get_gateway_status() -> dict:
    """Get hermes-gateway service status."""
    code, out, err = run_command(["systemctl", "--user", "status", "hermes-gateway", "--no-pager"], timeout=10)
    return parse_service_status(out, err, "hermes-gateway", user=True)


def get_dashboard_status() -> dict:
    """Get hermes-dashboard service status."""
    code, out, err = run_command(["systemctl", "--user", "status", "hermes-dashboard", "--no-pager"], timeout=10)
    return parse_service_status(out, err, "hermes-dashboard", user=True)


def parse_service_status(output: str, error: str, name: str, user: bool) -> dict:
    """Parse systemctl status output."""
    info = {
        "name": name,
        "user": user,
        "active": False,
        "sub_state": "",
        "main_pid": None,
        "memory": "",
        "cpu": "",
        "output": output,
        "error": error,
    }
    
    for line in output.split("\n"):
        if "Active:" in line:
            info["active"] = "active" in line.lower()
            if "active (running)" in line:
                info["sub_state"] = "running"
            elif "inactive" in line:
                info["sub_state"] = "inactive"
            elif "failed" in line:
                info["sub_state"] = "failed"
        if "Main PID:" in line:
            try:
                info["main_pid"] = int(line.split(":")[1].strip())
            except (ValueError, IndexError):
                pass
        if "Memory:" in line:
            info["memory"] = line.split(":", 1)[1].strip()
        if "CPU:" in line:
            info["cpu"] = line.split(":", 1)[1].strip()
    
    return info


def restart_gateway() -> dict:
    """Restart hermes-gateway service."""
    code, out, err = run_command(["systemctl", "--user", "restart", "hermes-gateway"], timeout=30)
    return {
        "action": "restart_gateway",
        "success": code == 0,
        "output": out,
        "error": err,
    }


def restart_dashboard() -> dict:
    """Restart hermes-dashboard service."""
    code, out, err = run_command(["systemctl", "--user", "restart", "hermes-dashboard"], timeout=30)
    return {
        "action": "restart_dashboard",
        "success": code == 0,
        "output": out,
        "error": err,
    }


def get_gateway_logs(lines: int = 50) -> str:
    """Get recent gateway logs."""
    code, out, err = run_command(
        ["journalctl", "--user", "-u", "hermes-gateway", "-n", str(lines), "--no-pager", "--output=short"],
        timeout=15,
    )
    if code == 0:
        return out
    return err or "No logs available"


def get_dashboard_logs(lines: int = 50) -> str:
    """Get recent dashboard logs."""
    code, out, err = run_command(
        ["journalctl", "--user", "-u", "hermes-dashboard", "-n", str(lines), "--no-pager", "--output=short"],
        timeout=15,
    )
    if code == 0:
        return out
    return err or "No logs available"


def get_hermes_info() -> dict:
    """Get Hermes version, skills, and other info."""
    version = get_hermes_version()
    skills = get_hermes_skills()
    return {
        "version": version,
        "skills": skills,
        "skills_count": len(skills),
        "hermes_home": os.path.expanduser("~/.hermes"),
        "hermes_bin": "/home/rahat/.local/bin/hermes",
    }


def get_hermes_sessions_summary() -> list[dict]:
    """
    Get a summary of recent Hermes sessions from state.db.
    This is a lightweight read-only query.
    """
    db_path = "/home/rahat/.hermes/state.db"
    if not os.path.isfile(db_path):
        return [{"note": "state.db not found"}]
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Try to get session count and recent sessions
        # The schema may vary — try common patterns
        sessions = []
        
        # Try sessions table
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%session%'")
            tables = [row[0] for row in cursor.fetchall()]
            
            if tables:
                for table in tables:
                    cursor.execute(f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT 20")
                    rows = cursor.fetchall()
                    if rows:
                        for row in rows:
                            sessions.append({
                                "table": table,
                                "data": dict(row),
                            })
        except Exception:
            pass
        
        # Fallback: try to get count from sessions table
        try:
            cursor.execute("SELECT COUNT(*) FROM sessions")
            count = cursor.fetchone()[0]
            sessions.append({"session_count": count})
        except Exception:
            pass
        
        conn.close()
        return sessions if sessions else [{"note": "No session data available"}]
    except Exception as e:
        return [{"error": str(e)}]


def get_cron_jobs() -> list[dict]:
    """
    List Hermes cron jobs from ~/.hermes/cron/.
    """
    cron_dir = "/home/rahat/.hermes/cron"
    jobs = []
    
    if not os.path.isdir(cron_dir):
        return [{"note": "No cron directory found"}]
    
    # Read executions database
    db_path = os.path.join(cron_dir, "executions.db")
    if os.path.isfile(db_path):
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                try:
                    cursor.execute(f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT 10")
                    rows = cursor.fetchall()
                    for row in rows:
                        jobs.append({
                            "source": "executions.db",
                            "table": table,
                            "data": dict(row),
                        })
                except Exception:
                    pass
            conn.close()
        except Exception:
            pass
    
    # Read ticker files
    ticker_files = ["ticker_heartbeat", "ticker_last_success"]
    for tf in ticker_files:
        path = os.path.join(cron_dir, tf)
        if os.path.isfile(path):
            try:
                with open(path, "r") as f:
                    content = f.read().strip()
                jobs.append({
                    "source": "ticker",
                    "file": tf,
                    "content": content,
                })
            except Exception:
                pass
    
    if not jobs:
        return [{"note": "No cron jobs found"}]
    
    return jobs


def get_memory_pressure() -> dict:
    """
    Check memory pressure status.
    Returns warning flags if swap is heavily used or RAM is low.
    """
    result = {
        "warning": False,
        "swap_used_pct": 0,
        "ram_used_pct": 0,
        "details": "",
    }
    
    try:
        with open("/proc/meminfo", "r") as f:
            meminfo = {}
            for line in f:
                parts = line.strip().split(": ")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip()
                    if val.endswith(" kB"):
                        val = int(val[:-3])
                    else:
                        try:
                            val = int(val)
                        except ValueError:
                            val = 0
                    meminfo[key] = val
        
        total = meminfo.get("MemTotal", 1)
        available = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
        swap_total = meminfo.get("SwapTotal", 0)
        swap_free = meminfo.get("SwapFree", 0)
        
        ram_used = total - available
        ram_pct = (ram_used / total * 100) if total > 0 else 0
        result["ram_used_pct"] = round(ram_pct, 1)
        
        if swap_total > 0:
            swap_used = swap_total - swap_free
            swap_pct = (swap_used / swap_total * 100) if swap_total > 0 else 0
            result["swap_used_pct"] = round(swap_pct, 1)
        
        # Warning thresholds
        if ram_pct > 85:
            result["warning"] = True
            result["details"] = f"High RAM usage: {ram_pct}%"
        if swap_total > 0 and swap_pct > 50:
            result["warning"] = True
            result["details"] = f"High swap usage: {swap_pct}%"
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


def get_network_quality() -> dict:
    """
    Check network quality by pinging gateway and 8.8.8.8.
    """
    from dashboard.services.network import ping_test, get_gateways
    
    gateways = get_gateways()
    gateway_ip = gateways[0]["gateway"] if gateways else None
    
    results = {
        "gateway": None,
        "internet": None,
        "overall": "unknown",
    }
    
    if gateway_ip:
        gw_result = ping_test(gateway_ip, count=2)
        results["gateway"] = {
            "target": gateway_ip,
            "success": gw_result["success"],
            "avg_latency": gw_result["avg_latency"],
        }
    
    internet_result = ping_test("8.8.8.8", count=2)
    results["internet"] = {
        "target": "8.8.8.8",
        "success": internet_result["success"],
        "avg_latency": internet_result["avg_latency"],
    }
    
    # Overall assessment
    if results["gateway"]["success"] and results["internet"]["success"]:
        results["overall"] = "good"
    elif results["gateway"]["success"]:
        results["overall"] = "local_only"
    elif results["internet"]["success"]:
        results["overall"] = "no_gateway"
    else:
        results["overall"] = "no_connection"
    
    return results
