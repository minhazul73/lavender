import os
import stat
import tempfile
from unittest.mock import patch

from server.services.files import get_quick_bookmarks


def test_get_quick_bookmarks_includes_user_and_system(tmp_path):
    user_home = str(tmp_path / "fakehome")
    os.makedirs(os.path.join(user_home, "Documents"), exist_ok=True)

    bookmarks = get_quick_bookmarks(user_home=user_home)

    paths = [b["path"] for b in bookmarks]
    names = [b["name"] for b in bookmarks]

    assert user_home in paths
    assert "Documents" in names
    # Verify temp bookmark exists and points to real temp directory
    real_tmp = os.path.realpath(tempfile.gettempdir())
    assert real_tmp in paths
    assert any(b["name"] == "Temp" for b in bookmarks)


def test_get_quick_bookmarks_skips_invalid_temp(tmp_path):
    user_home = str(tmp_path / "fakehome")
    os.makedirs(user_home, exist_ok=True)

    # If stat raises OSError on temp directory or it's not a dir
    fake_stat = os.stat(str(tmp_path))
    non_dir_stat = os.stat_result((
        stat.S_IFREG | 0o644,  # Not a directory
        fake_stat.st_ino,
        fake_stat.st_dev,
        fake_stat.st_nlink,
        fake_stat.st_uid,
        fake_stat.st_gid,
        fake_stat.st_size,
        fake_stat.st_atime,
        fake_stat.st_mtime,
        fake_stat.st_ctime,
    ))

    real_tmp = os.path.realpath(tempfile.gettempdir())
    orig_stat = os.stat

    def mocked_stat(path, *args, **kwargs):
        if path == real_tmp:
            return non_dir_stat
        return orig_stat(path, *args, **kwargs)

    with patch("os.stat", side_effect=mocked_stat):
        bookmarks = get_quick_bookmarks(user_home=user_home)
        assert not any(b["path"] == real_tmp for b in bookmarks)
