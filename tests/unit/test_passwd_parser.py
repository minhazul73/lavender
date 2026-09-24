import os
from server.utils.passwd import parse_all_passwd_users, parse_groups, parse_passwd_users

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
