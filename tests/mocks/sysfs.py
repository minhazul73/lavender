from typing import Optional


class MockSysfsReader:
    """In-memory sysfs and procfs reader for testing."""

    def __init__(self, initial_files: Optional[dict[str, str]] = None):
        self.files: dict[str, str] = dict(initial_files or {})
        self.directories: dict[str, list[str]] = {}

    def set_file(self, path: str, content: str) -> None:
        self.files[path] = content

    def set_dir(self, path: str, entries: list[str]) -> None:
        self.directories[path] = sorted(entries)

    def read_file(self, path: str) -> Optional[str]:
        return self.files.get(path)

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
        if path in self.directories:
            return list(self.directories[path])
        # Auto-discover from files
        prefix = path.rstrip("/") + "/"
        entries = set()
        for f in self.files:
            if f.startswith(prefix):
                rel = f[len(prefix):].split("/")[0]
                if rel:
                    entries.add(rel)
        return sorted(list(entries))

    def exists(self, path: str) -> bool:
        return path in self.files or path in self.directories or any(f.startswith(path.rstrip("/") + "/") for f in self.files)
