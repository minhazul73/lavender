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
    stat_mock = MagicMock()
    stat_mock.f_blocks = 1000
    stat_mock.f_bfree = 200
    stat_mock.f_frsize = 1024 * 1024  # 800 MB used

    def fake_run_sync(cmd, timeout=30.0):
        target = cmd[-1]
        if target == "/home":
            stdout = "1.2G\t/home/alice\x003.0G\t/home/bob\x004.2G\t/home\x00"
        elif target == "/var":
            stdout = "500M\t/var/log\x001.5G\t/var/lib\x002.0G\t/var\x00"
        elif target == "/tmp":
            stdout = "10M\t/tmp/dir\nwith\nnewlines\x0040M\t/tmp/cache\x0050M\t/tmp\x00"
        else:
            stdout = ""
        return CommandResult(0, stdout, "")

    with patch("os.statvfs", return_value=stat_mock), patch("server.services.storage.get_executor") as mock_get_executor:
        mock_executor = MagicMock()
        mock_executor.run_sync.side_effect = fake_run_sync
        mock_get_executor.return_value = mock_executor

        usages = get_dir_usage()
        assert len(usages) == 4

        # Root path uses statvfs
        assert usages[0]["base_path"] == "/"
        assert usages[0]["total_size"] == "800M"
        assert usages[0]["directories"] == [{"path": "/", "size": "800M"}]

        # Folder inspection uses du -h -0 --max-depth=1
        assert usages[1]["base_path"] == "/home"
        assert usages[1]["total_size"] == "4.2G"
        assert usages[1]["directories"] == [
            {"path": "/home/alice", "size": "1.2G"},
            {"path": "/home/bob", "size": "3.0G"},
            {"path": "/home", "size": "4.2G"},
        ]

        assert usages[2]["base_path"] == "/var"
        assert usages[2]["total_size"] == "2.0G"
        assert usages[2]["directories"] == [
            {"path": "/var/log", "size": "500M"},
            {"path": "/var/lib", "size": "1.5G"},
            {"path": "/var", "size": "2.0G"},
        ]

        # Directory with embedded newlines preserved verbatim
        assert usages[3]["base_path"] == "/tmp"
        assert usages[3]["total_size"] == "50M"
        assert usages[3]["directories"] == [
            {"path": "/tmp/dir\nwith\nnewlines", "size": "10M"},
            {"path": "/tmp/cache", "size": "40M"},
            {"path": "/tmp", "size": "50M"},
        ]

        assert mock_executor.run_sync.call_count == 3
        mock_executor.run_sync.assert_any_call(["du", "-h", "-0", "--max-depth=1", "/home"], timeout=30.0)
        mock_executor.run_sync.assert_any_call(["du", "-h", "-0", "--max-depth=1", "/var"], timeout=30.0)
        mock_executor.run_sync.assert_any_call(["du", "-h", "-0", "--max-depth=1", "/tmp"], timeout=30.0)


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

