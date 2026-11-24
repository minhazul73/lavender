"""
Storage utilities: disk usage via df -h, mount info, and directory usage.
"""
import os
import re
from typing import Any

from server.core.executor import get_executor

SYSTEM_ROOTS = frozenset(["/", "/proc", "/sys", "/dev"])
PSEUDO_FS = frozenset([
    "tmpfs", "devtmpfs", "devpts", "proc", "sysfs", "cgroup", "cgroup2",
    "debugfs", "tracefs", "fusectl", "pstore", "bpf", "configfs", "securityfs",
    "hugetlbfs", "dev", "run",
])
HIDDEN_MOUNTS = frozenset(["/boot"])
HIDDEN_MOUNT_PREFIXES = ("/run/msm-firmware-loader/", "/run/docker/", "/var/lib/docker/")
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


def _run_df() -> list[dict[str, Any]]:
    """Run 'df -h' and parse output, filtering pseudo FSes and hidden mounts.

    Returns a list of dicts with keys: fs, size, used, avail, use_pct,
    mount, is_external, pct_num.
    """
    try:
        result = get_executor().run_sync(
            ["df", "-h"],
            timeout=10.0,
        )
        if result.returncode != 0:
            return []
        lines = result.stdout.strip().split('\n')
        if len(lines) < 2:
            return []

        entries: list[dict[str, Any]] = []
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
                "filesystem": fs,
                "size": parts[1],
                "used": parts[2],
                "avail": parts[3],
                "available": parts[3],
                "use_pct": use_pct_str,
                "use_percent": use_pct_str,
                "mount": mount,
                "mount_point": mount,
                "is_external": _is_external_mount(mount),
                "pct_num": _parse_pct(use_pct_str),
            })

        # Deduplicate by device: keep the entry with the shortest mount path
        seen: dict[str, dict[str, Any]] = {}
        for e in entries:
            device = e["fs"]
            mount_path = e.get("mount") or e.get("mount_point") or ""
            if device not in seen:
                seen[device] = e
            else:
                prev_mount = seen[device].get("mount") or seen[device].get("mount_point") or ""
                if len(mount_path) < len(prev_mount):
                    seen[device] = e

        return list(seen.values())
    except Exception:
        return []


def get_disk_usage() -> list[dict[str, Any]]:
    """Get disk usage from df -h, with external storage categorization."""
    return _run_df()


def get_mounts() -> list[dict[str, str]]:
    """Read /proc/mounts for mount info, filtering pseudo FSes."""
    mounts = []
    try:
        with open('/proc/mounts') as f:
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


def _format_size(num_bytes: int | float) -> str:
    """Format byte count to human-readable string matching du/df output."""
    if num_bytes <= 0:
        return "0B"
    for unit in ["B", "K", "M", "G", "T", "P"]:
        if abs(num_bytes) < 1024.0 or unit == "P":
            if unit == "B":
                return f"{int(num_bytes)}B"
            val = round(num_bytes, 1)
            if val == int(val):
                return f"{int(val)}{unit}"
            return f"{val:.1f}{unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f}P"


def _statvfs_usage(path: str) -> dict[str, Any]:
    """Acquire filesystem usage via statvfs for partition root."""
    try:
        st = os.statvfs(path)
        size = _format_size((st.f_blocks - st.f_bfree) * st.f_frsize)
        return {"base_path": path, "total_size": size, "directories": [{"path": path, "size": size}]}
    except Exception:
        return {"base_path": path, "total_size": "?", "directories": []}


def _parse_du_records(stdout: str, base_path: str) -> tuple[list[dict[str, str]], str]:
    """Parse NUL-delimited records from du stdout preserving embedded newlines in paths."""
    dirs: list[dict[str, str]] = []
    total_size = "?"
    for record in stdout.split("\x00"):
        if not record:
            continue
        parts = record.split("\t", 1)
        if len(parts) == 2:
            entry_size, entry_path = parts[0].strip(), parts[1]
            dirs.append({"path": entry_path, "size": entry_size})
            if entry_path == base_path:
                total_size = entry_size
    if total_size == "?" and dirs:
        total_size = dirs[-1]["size"]
    return dirs, total_size


def _query_dir_usage(path: str) -> dict[str, Any]:
    """Execute du and construct directory usage record with fallback."""
    try:
        p = get_executor().run_sync(["du", "-h", "-0", "--max-depth=1", path], timeout=30.0)
        if p.returncode == 0 and p.stdout:
            dirs, total_size = _parse_du_records(p.stdout, path)
            return {
                "base_path": path,
                "total_size": total_size,
                "directories": dirs or [{"path": path, "size": total_size}],
            }
    except Exception:
        pass
    return {"base_path": path, "total_size": "?", "directories": []}


def get_dir_usage() -> list[dict[str, Any]]:
    """Get directory usage via statvfs for partitions and du --max-depth=1 for folders."""
    paths = ["/", "/home", "/var", os.path.join(os.sep, "tmp")]
    return [_statvfs_usage(p) if p == "/" else _query_dir_usage(p) for p in paths]


def _decode_mount_path(path: str) -> str:
    """Decode octal escape sequences used by the Linux kernel in /proc/mounts."""
    return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), path)


def unmount(mount_point: str) -> dict[str, Any]:
    """Verify mount point in /proc/mounts and unmount filesystem.

    Args:
        mount_point: Path to the mounted filesystem or device.

    Returns:
        Dict with success status and either command output or error message.
    """
    target = os.path.normpath(mount_point) if mount_point and mount_point.strip() else ""
    real_target = os.path.realpath(target) if target else ""
    if (
        not target
        or target in SYSTEM_ROOTS
        or target.startswith(("/proc/", "/sys/", "/dev/"))
        or real_target in SYSTEM_ROOTS
        or real_target.startswith(("/proc/", "/sys/", "/dev/"))
    ):
        return {"success": False, "error": f"Refusing to unmount system root: {mount_point}"}

    is_mounted = False
    try:
        with open("/proc/mounts", encoding="utf-8", errors="surrogateescape") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 2:
                    mp = _decode_mount_path(parts[1])
                    if mp == target or mp == real_target:
                        is_mounted = True
                        break
    except Exception as e:
        return {"success": False, "error": f"Cannot verify mount point: {e}"}

    if not is_mounted:
        return {"success": False, "error": f"Mount point '{target}' is not mounted"}

    try:
        result = get_executor().run_sync(
            ["sudo", "-n", "umount", target],
            timeout=30.0,
        )
        if result.returncode == 0:
            return {"success": True, "output": result.stdout}
        return {"success": False, "error": result.stderr.strip() or "umount failed"}
    except Exception as e:
        return {"success": False, "error": str(e)}
