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

# Mount paths to exclude from user-facing storage list
HIDDEN_MOUNTS = frozenset([
    "/boot",            # system partition, not useful for users
])

# Mount path prefixes to exclude (firmware, system internals)
HIDDEN_MOUNT_PREFIXES = (
    "/run/msm-firmware-loader/",
    "/run/docker/",
    "/var/lib/docker/",
)

# Mount path prefixes considered "external" / user-accessible storage
EXTERNAL_PREFIXES = ("/mnt/", "/media/", "/storage/", "/sdcard", "/external")


def _is_external_mount(mount: str) -> bool:
    """Check if a mount point is external/user-accessible storage."""
    if mount in HIDDEN_MOUNTS:
        return False
    return any(mount.startswith(p) for p in EXTERNAL_PREFIXES) or mount == "/mnt/sdcard"


def _parse_pct(pct_str: str):
    """Parse a percentage string like '34%' into an integer 34."""
    try:
        return int(pct_str.rstrip('%'))
    except (ValueError, AttributeError):
        return 0


def _run_df() -> List[Dict[str, Any]]:
    """Run 'df -h' and parse output, filtering pseudo FSes and hidden mounts.

    Returns a list of dicts with keys: fs, size, used, avail, use_pct,
    mount, is_external, pct_num.
    """
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

        entries: List[Dict[str, Any]] = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 6:
                continue
            fs = parts[0]
            fs_base = fs.split('/')[-1] if '/' in fs else fs
            if fs_base in PSEUDO_FS:
                continue
            mount = parts[5]
            if mount in HIDDEN_MOUNTS:
                continue
            if any(mount.startswith(p) for p in HIDDEN_MOUNT_PREFIXES):
                continue
            use_pct_str = parts[4]
            entries.append({
                "fs": fs,
                "size": parts[1],
                "used": parts[2],
                "avail": parts[3],
                "use_pct": use_pct_str,
                "mount": mount,
                "is_external": _is_external_mount(mount),
                "pct_num": _parse_pct(use_pct_str),
            })

        # Deduplicate by device: keep the entry with the shortest mount path
        seen: Dict[str, Dict[str, Any]] = {}
        for e in entries:
            device = e["fs"]
            if device not in seen:
                seen[device] = e
            elif len(e["mount"]) < len(seen[device]["mount"]):
                seen[device] = e

        return list(seen.values())
    except Exception:
        return []


def get_disk_usage() -> List[Dict[str, Any]]:
    """Get disk usage from df -h, with external storage categorization."""
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
