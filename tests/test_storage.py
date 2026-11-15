from unittest.mock import MagicMock, mock_open, patch

from server.core.executor import CommandResult
from server.services.storage import get_dir_usage, get_disk_usage, unmount


def test_get_disk_usage_uses_executor():
    df_output = (
        "Filesystem     Size  Used Avail Use% Mounted on\n"
        "/dev/sda1       50G   20G   28G  42% /\n"
        "/dev/sdb1      100G   10G   85G  11% /mnt/data\n"
    )
    with patch("server.services.storage.get_executor") as mock_get_executor:
        mock_executor = MagicMock()
        mock_executor.run_sync.return_value = CommandResult(0, df_output, "")
        mock_get_executor.return_value = mock_executor

        disks = get_disk_usage()
        assert len(disks) == 2
        assert disks[0]["mount_point"] == "/"
        assert disks[0]["used"] == "20G"
        assert disks[1]["mount_point"] == "/mnt/data"
        assert disks[1]["is_external"] is True
        mock_executor.run_sync.assert_called_once_with(["df", "-h"], timeout=10.0)


def test_get_dir_usage_uses_executor():
    with patch("server.services.storage.get_executor") as mock_get_executor:
        mock_executor = MagicMock()
        mock_executor.run_sync.return_value = CommandResult(0, "4.2G\t/home", "")
        mock_get_executor.return_value = mock_executor

        usages = get_dir_usage()
        assert len(usages) == 4
        assert usages[1]["base_path"] == "/home"
        assert usages[1]["total_size"] == "4.2G"
        assert mock_executor.run_sync.call_count == 4


def test_unmount_uses_executor():
    proc_mounts_content = "/dev/sdb1 /mnt/data ext4 rw 0 0\n"
    with patch("builtins.open", mock_open(read_data=proc_mounts_content)):
        with patch("server.services.storage.get_executor") as mock_get_executor:
            mock_executor = MagicMock()
            mock_executor.run_sync.return_value = CommandResult(0, "unmounted", "")
            mock_get_executor.return_value = mock_executor

            res = unmount("/mnt/data")

            assert res["success"] is True
            mock_executor.run_sync.assert_called_once_with(["sudo", "-n", "umount", "/mnt/data"], timeout=30.0)

