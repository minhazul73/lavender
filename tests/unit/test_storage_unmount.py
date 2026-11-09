import builtins
import os
import subprocess
import tempfile
from unittest.mock import mock_open, patch

from server.services.storage import _decode_mount_path, unmount


def test_decode_mount_path_octal_escapes():
    """Verify decoding of kernel octal escape sequences (space, tab, newline, backslash)."""
    # Test spaces (\040), tabs (\011), newlines (\012), backslashes (\134)
    raw = r"/mnt/space\040dir/tab\011dir/newline\012dir/backslash\134dir"
    expected = "/mnt/space dir/tab\tdir/newline\ndir/backslash\\dir"
    assert _decode_mount_path(raw) == expected


def test_unmount_blank_input_rejected():
    """Verify empty or whitespace-only mount points are rejected."""
    res1 = unmount("")
    assert res1["success"] is False
    assert "Refusing to unmount" in res1["error"]

    res2 = unmount("   ")
    assert res2["success"] is False
    assert "Refusing to unmount" in res2["error"]


def test_unmount_system_root_rejected():
    """Verify protected system root paths and pseudo-filesystems are rejected."""
    res = unmount("/")
    assert res["success"] is False
    assert "Refusing to unmount system root" in res["error"]

    res_proc = unmount("/proc")
    assert res_proc["success"] is False

    res_sys = unmount("/sys/fs/cgroup")
    assert res_sys["success"] is False


def test_unmount_trailing_whitespace_preserved():
    """Verify trailing whitespace in valid mount paths is preserved for matching and umount."""
    # Mount point has a trailing space: "/mnt/external "
    proc_mounts_content = (
        "/dev/sdb1 /mnt/external\\040 ext4 rw,relatime 0 0\n"
    )
    with patch("builtins.open", mock_open(read_data=proc_mounts_content)):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["sudo", "umount", "/mnt/external "],
                returncode=0,
                stdout="unmounted",
                stderr="",
            )
            res = unmount("/mnt/external ")
            assert res["success"] is True
            mock_run.assert_called_once_with(
                ["sudo", "umount", "/mnt/external "],
                capture_output=True,
                text=True,
                timeout=30,
            )


def test_unmount_escaped_path_decoded_and_compared():
    """Verify escaped mount paths from /proc/mounts are decoded before comparison."""
    # Mount point with space and backslash
    proc_mounts_content = (
        "/dev/sdc1 /media/usb\\134disk\\040drive ext4 rw 0 0\n"
    )
    with patch("builtins.open", mock_open(read_data=proc_mounts_content)):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["sudo", "umount", "/media/usb\\disk drive"],
                returncode=0,
                stdout="unmounted",
                stderr="",
            )
            res = unmount("/media/usb\\disk drive")
            assert res["success"] is True
            mock_run.assert_called_once_with(
                ["sudo", "umount", "/media/usb\\disk drive"],
                capture_output=True,
                text=True,
                timeout=30,
            )


def test_unmount_symlink_to_system_root_rejected():
    """Verify symlinks resolving to system roots are rejected."""
    with patch("os.path.realpath", return_value="/proc/sys"):
        res = unmount("/mnt/fake_proc")
        assert res["success"] is False
        assert "Refusing to unmount system root" in res["error"]


def test_unmount_surrogateescape_handling():
    """Verify mount point matching succeeds when /proc/mounts contains undecodable bytes."""
    # Provide raw mount-entry bytes containing non-UTF-8 byte (\xe9)
    raw_mount_bytes = b"/dev/sdd1 /media/caf\xe9 ext4 rw 0 0\n"
    with tempfile.NamedTemporaryFile("wb", delete=False) as tf:
        tf.write(raw_mount_bytes)
        temp_path = tf.name

    orig_open = builtins.open

    def custom_open(file, *args, **kwargs):
        """Intercept /proc/mounts to read from temporary raw-byte file."""
        if file == "/proc/mounts":
            return orig_open(temp_path, *args, **kwargs)
        return orig_open(file, *args, **kwargs)

    decoded_target = "/media/caf\udce9"

    try:
        with patch("builtins.open", side_effect=custom_open):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = subprocess.CompletedProcess(
                    args=["sudo", "umount", decoded_target],
                    returncode=0,
                    stdout="unmounted",
                    stderr="",
                )
                res = unmount(decoded_target)
                assert res["success"] is True
                mock_run.assert_called_once_with(
                    ["sudo", "umount", decoded_target],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
