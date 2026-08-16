"""
Storage utilities: disk usage via df -h, mount info, and directory usage.
"""
import subprocess
from typing import List, Dict, Any


PSEUDO_FS = frozenset([
    "tmpfs", "devtmpfs", "devpts", "proc", "sysfs", "cgroup",
    "cgroup2", "debugfs", "tracefs", "fusectl", "pstore",
    "bpf", "configfs", "securityfs", "hugetlbfs",
    "dev", "run",  # pseudo mounts with no device prefix
])


def _run_df() -> List[Dict[str, str]]:
    """Run 'df -h' and parse output, filtering pseudo FSes and deduplicating
    bind mounts (keep only the root mount for each physical device)."""
    try:
        result = subprocess.run(
            ["df", "-h"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        lines = result.stdout.strip().split('\n')
        if len(lines) < 2:
            return []

        entries: List[Dict[str, str]] = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 6:
                continue
            fs = parts[0]
            fs_base = fs.split('/')[-1] if '/' in fs else fs
            if fs_base in PSEUDO_FS:
                continue
            entries.append({
                "fs": fs,
                "size": parts[1],
                "used": parts[2],
                "avail": parts[3],
                "use_pct": parts[4],
                "mount": parts[5],
            })

        # Deduplicate by device: keep the entry with the shortest mount path
        seen: Dict[str, Dict[str, str]] = {}
        for e in entries:
            device = e["fs"]
            if device not in seen:
                seen[device] = e
            elif len(e["mount"]) < len(seen[device]["mount"]):
                seen[device] = e

        return list(seen.values())
    except Exception:
        return []


def get_disk_usage() -> List[Dict[str, str]]:
    """Get disk usage from df -h."""
    return _run_df()


def get_mounts() -> List[Dict[str, str]]:
    """Read /proc/mounts for mount info, filtering pseudo FSes."""
    mounts = []
    try:
        with open('/proc/mounts', 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 4:
                    fs = parts[2]
                    fs_base = fs.split('/')[-1] if '/' in fs else fs
                    if fs_base in PSEUDO_FS:
                        continue
                    mounts.append({
                        "source": parts[0],
                        "target": parts[1],
                        "fs": fs,
                        "options": parts[3],
                    })
    except Exception:
        pass
    return mounts


def get_dir_usage() -> List[Dict[str, Any]]:
    """Get directory usage via du -sh on common paths."""
    paths = ['/', '/home', '/var', '/tmp']
    result = []
    for path in paths:
        try:
            p = subprocess.run(
                ["du", "-sh", path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            size = p.stdout.strip().split()[0] if p.stdout.strip() else '?'
            result.append({
                "base_path": path,
                "total_size": size,
                "directories": [{"path": path, "size": size}],
            })
        except Exception:
            result.append({
                "base_path": path,
                "total_size": '?',
                "directories": [],
            })
    return result


def unmount(mount_point: str) -> Dict[str, Any]:
    """Unmount a filesystem (requires sudo)."""
    try:
        result = subprocess.run(
            ["sudo", "umount", mount_point],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return {"success": True, "output": result.stdout}
        return {"success": False, "error": result.stderr.strip() or "umount failed"}
    except Exception as e:
        return {"success": False, "error": str(e)}
