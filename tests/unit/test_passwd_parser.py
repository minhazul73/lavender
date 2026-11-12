import os
from unittest.mock import MagicMock, patch

from server.utils.passwd import (
    get_user_groups,
    parse_all_passwd_users,
    parse_groups,
    parse_passwd_users,
)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "mocks", "fixtures")


def test_parse_passwd_users():
    passwd_path = os.path.join(FIXTURES_DIR, "etc_passwd.txt")
    users = parse_passwd_users(min_uid=1000, exclude_nologin=True, path=passwd_path)

    # Should find rahat (1000) and alpinist (1001)
    # Should exclude nobody (65534) and serviceuser (which has shell /bin/false)
    names = [u["name"] for u in users]
    assert "rahat" in names
    assert "alpinist" in names
    assert "nobody" not in names
    assert "serviceuser" not in names
    assert "bin" not in names


def test_parse_all_passwd_users():
    passwd_path = os.path.join(FIXTURES_DIR, "etc_passwd.txt")
    all_users = parse_all_passwd_users(path=passwd_path)

    user_map = {u["name"]: u for u in all_users}
    assert "root" in user_map
    assert user_map["root"]["is_human"] is True  # root is marked human / admin
    assert user_map["rahat"]["is_human"] is True
    assert user_map["daemon"]["is_human"] is False
    assert user_map["nobody"]["is_human"] is False
    assert user_map["serviceuser"]["is_human"] is False


def test_parse_groups():
    group_path = os.path.join(FIXTURES_DIR, "etc_group.txt")
    groups = parse_groups(path=group_path)

    group_map = {g["name"]: g for g in groups}
    assert "wheel" in group_map
    assert "rahat" in group_map["wheel"]["members"]
    assert "alpinist" in group_map["wheel"]["members"]
    assert group_map["sudo"]["gid"] == 27


def test_get_user_groups_single_pass():
    g_primary = MagicMock()
    g_primary.gr_name = "usergroup"
    g_primary.gr_gid = 1000
    g_primary.gr_mem = []

    g_secondary = MagicMock()
    g_secondary.gr_name = "wheel"
    g_secondary.gr_gid = 10
    g_secondary.gr_mem = ["testuser"]

    with patch("grp.getgrall", return_value=[g_primary, g_secondary]) as mock_grall, \
         patch("grp.getgrgid") as mock_grgid:
        groups = get_user_groups("testuser", primary_gid=1000)
        assert groups == ["usergroup", "wheel"]
        mock_grall.assert_called_once()
        mock_grgid.assert_not_called()  # Proves single-pass without extra getgrgid lookup


def test_get_user_groups_dedup_and_fallback():
    g_both = MagicMock()
    g_both.gr_name = "sharedgroup"
    g_both.gr_gid = 1000
    g_both.gr_mem = ["testuser"]

    with patch("grp.getgrall", return_value=[g_both]):
        groups = get_user_groups("testuser", primary_gid=1000)
        # Should not duplicate primary group
        assert groups == ["sharedgroup"]

    # Test fallback when primary_gid is missing from getgrall
    g_fallback = MagicMock()
    g_fallback.gr_name = "fallbackgroup"
    with patch("grp.getgrall", return_value=[]), \
         patch("grp.getgrgid", return_value=g_fallback) as mock_grgid:
        groups = get_user_groups("testuser", primary_gid=2000)
        assert groups == ["fallbackgroup"]
        mock_grgid.assert_called_once_with(2000)

