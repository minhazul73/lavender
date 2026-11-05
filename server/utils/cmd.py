"""
Command resolution and presence checks.
"""
import shutil


def which(name: str) -> str | None:
    """Find program in PATH, return full path or None."""
    return shutil.which(name)


def has_command(name: str) -> bool:
    """Return True if command is executable in PATH."""
    return shutil.which(name) is not None
