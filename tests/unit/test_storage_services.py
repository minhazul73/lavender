"""
Unit tests for dashboard.services.storage.
"""
from unittest.mock import patch, mock_open

from dashboard.services import storage


class TestIsExternalMount:
    def test_mnt_is_external(self):
        assert storage._is_external_mount("/mnt/data") is True

    def test_media_is_external(self):
        assert storage._is_external_mount("/media/usb") is True

    def test_sdcard_is_external(self):
        assert storage._is_external_mount("/mnt/sdcard") is True

    def test_boot_is_hidden(self):
        assert storage._is_external_mount("/boot") is False

    def test_root_is_not_external(self):
        assert storage._is_external_mount("/") is False

    def test_home_is_not_external(self):
        assert storage._is_external_mount("/home") is False


class TestParsePct:
    def test_valid_percentage(self):
        assert storage._parse_pct("45%") == 45

    def test_zero_percentage(self):
        assert storage._parse_pct("0%") == 0

    def test_hundred_percentage(self):
        assert storage._parse_pct("100%") == 100

    def test_invalid_string(self):
        assert storage._parse_pct("abc") == 0

    def test_empty_string(self):
        assert storage._parse_pct("") == 0

    def test_none_type(self):
        assert storage._parse_pct(None) == 0


class TestRunDf:
    @patch("subprocess.run")
    def test_parses_df_output(self, mock_run):
        df_out = (
            "Filesystem      Size  Used Avail Use% Mounted on\n"
            "/dev/mmcblk0p1   48G   20G   26G  44% /\n"
            "tmpfs           1.7G     0  1.7G   0% /dev/shm\n"
            "/dev/sda1        64G   10G   54G  16% /mnt/sdcard\n"
        )
        mock_run.return_value = type("R", (), {
            "stdout": df_out, "returncode": 0
        })()
        result = storage._run_df()
        # tmpfs should be filtered out
        fs_list = [e["fs"] for e in result]
        assert "tmpfs" not in fs_list
        assert len(result) == 2
        root_entry = [e for e in result if e["mount"] == "/"][0]
        assert root_entry["size"] == "48G"
        assert root_entry["used"] == "20G"
        assert root_entry["avail"] == "26G"
        assert root_entry["use_pct"] == "44%"
        assert root_entry["pct_num"] == 44
        assert root_entry["is_external"] is False

    @patch("subprocess.run")
    def test_external_mount_flagged(self, mock_run):
        df_out = (
            "Filesystem  Size  Used Avail Use% Mounted on\n"
            "/dev/sda1   64G   10G   54G  16% /mnt/sdcard\n"
        )
        mock_run.return_value = type("R", (), {
            "stdout": df_out, "returncode": 0
        })()
        result = storage._run_df()
        assert len(result) == 1
        assert result[0]["is_external"] is True

    @patch("subprocess.run")
    def test_hidden_mount_filtered(self, mock_run):
        df_out = (
            "Filesystem  Size  Used Avail Use% Mounted on\n"
            "/dev/sda1   48G   20G   26G  44% /boot\n"
        )
        mock_run.return_value = type("R", (), {
            "stdout": df_out, "returncode": 0
        })()
        result = storage._run_df()
        mounts = [e["mount"] for e in result]
        assert "/boot" not in mounts

    @patch("subprocess.run")
    def test_deduplication_keeps_shortest_mount(self, mock_run):
        df_out = (
            "Filesystem  Size  Used Avail Use% Mounted on\n"
            "/dev/sda1   64G   10G   54G  16% /mnt\n"
            "/dev/sda1   64G   10G   54G  16% /mnt/data\n"
        )
        mock_run.return_value = type("R", (), {
            "stdout": df_out, "returncode": 0
        })()
        result = storage._run_df()
        assert len(result) == 1
        assert result[0]["mount"] == "/mnt"

    @patch("subprocess.run")
    def test_exception_returns_empty(self, mock_run):
        mock_run.side_effect = Exception("df failed")
        result = storage._run_df()
        assert result == []

    @patch("subprocess.run")
    def test_empty_output_returns_empty(self, mock_run):
        mock_run.return_value = type("R", (), {
            "stdout": "", "returncode": 0
        })()
        result = storage._run_df()
        assert result == []


class TestGetDiskUsage:
    @patch("dashboard.services.storage._run_df")
    def test_delegates_to_run_df(self, mock_run_df):
        mock_run_df.return_value = [{"fs": "/dev/sda1"}]
        result = storage.get_disk_usage()
        assert len(result) == 1
        mock_run_df.assert_called_once()

    @patch("dashboard.services.storage._run_df")
    def test_exception_returns_empty(self, mock_run_df):
        mock_run_df.side_effect = Exception("fail")
        result = storage.get_disk_usage()
        assert result == []


class TestGetMounts:
    @patch("builtins.open", new_callable=mock_open, read_data=(
        "/dev/mmcblk0p1 / ext4 rw,relatime 0 0\n"
        "tmpfs /dev/shm tmpfs rw,nosuid,nodev 0 0\n"
        "proc /proc proc rw,nosuid,nodev,noexec 0 0\n"
    ))
    def test_filters_pseudo_fs(self, mock_file):
        result = storage.get_mounts()
        fs_types = [m["fs"] for m in result]
        assert "tmpfs" not in fs_types
        assert "proc" not in fs_types
        assert "ext4" in fs_types
        assert len(result) == 1
        assert result[0]["source"] == "/dev/mmcblk0p1"
        assert result[0]["target"] == "/"

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_missing_proc_mounts(self, mock_file):
        result = storage.get_mounts()
        assert result == []


class TestGetDirUsage:
    @patch("subprocess.run")
    def test_parses_du_output(self, mock_run):
        mock_run.return_value = type("R", (), {
            "stdout": "4.2G\t/\n", "returncode": 0
        })()
        result = storage.get_dir_usage()
        assert len(result) == 4  # /, /home, /var, /tmp
        assert result[0]["base_path"] == "/"
        assert result[0]["total_size"] == "4.2G"

    @patch("subprocess.run")
    def test_du_failure_returns_question_mark(self, mock_run):
        mock_run.side_effect = Exception("du failed")
        result = storage.get_dir_usage()
        assert all(r["total_size"] == "?" for r in result)


class TestUnmount:
    @patch("subprocess.run")
    def test_unmount_success(self, mock_run):
        mock_run.return_value = type("R", (), {
            "stdout": "", "stderr": "", "returncode": 0
        })()
        res = storage.unmount("/mnt/usb")
        assert res["success"] is True

    @patch("subprocess.run")
    def test_unmount_failure(self, mock_run):
        mock_run.return_value = type("R", (), {
            "stdout": "", "stderr": "umount: not mounted", "returncode": 1
        })()
        res = storage.unmount("/mnt/usb")
        assert res["success"] is False
        assert "not mounted" in res["error"]

    @patch("subprocess.run")
    def test_unmount_exception(self, mock_run):
        mock_run.side_effect = Exception("timeout")
        res = storage.unmount("/mnt/usb")
        assert res["success"] is False
        assert "timeout" in res["error"]
