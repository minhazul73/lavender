import os
from typing import Optional, Protocol


class SysfsReader(Protocol):
    """Mockable interface for reading sysfs and procfs files."""

    def read_file(self, path: str) -> Optional[str]:
        """Read a sysfs/procfs file, return None on failure."""
        ...

    def read_int(self, path: str, default: int = 0) -> int:
        """Read an integer from a sysfs/procfs file."""
        ...

    def read_float(self, path: str, default: float = 0.0) -> float:
        """Read a float from a sysfs/procfs file."""
        ...

    def list_dir(self, path: str) -> list[str]:
        """List directory contents."""
        ...

    def exists(self, path: str) -> bool:
        """Check if path exists."""
        ...


class SystemSysfsReader:
    """Production reader using real Linux filesystem."""

    def read_file(self, path: str) -> Optional[str]:
        try:
            with open(path, "r", errors="replace") as f:
                return f.read().strip()
        except (FileNotFoundError, PermissionError, OSError):
            return None

    def read_int(self, path: str, default: int = 0) -> int:
        s = self.read_file(path)
        if s is None:
            return default
        try:
            return int(s.split()[0] if s else 0)
        except (ValueError, IndexError):
            return default

    def read_float(self, path: str, default: float = 0.0) -> float:
        s = self.read_file(path)
        if s is None:
            return default
        try:
            return float(s.split()[0] if s else 0.0)
        except (ValueError, IndexError):
            return default

    def list_dir(self, path: str) -> list[str]:
        try:
            return sorted(os.listdir(path))
        except (FileNotFoundError, PermissionError, OSError):
            return []

    def exists(self, path: str) -> bool:
        return os.path.exists(path)


_reader: SysfsReader = SystemSysfsReader()


def get_sysfs_reader() -> SysfsReader:
    return _reader


def set_sysfs_reader(reader: SysfsReader) -> None:
    global _reader
    _reader = reader
