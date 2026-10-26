"""
Unit tests for dashboard.services.users.
"""
from unittest.mock import patch, mock_open

from dashboard.services import users as users_svc


class TestSshPath:
    def test_root_path(self):
        assert users_svc.get_user_ssh_path("root") == "/root/.ssh/authorized_keys"

    def test_normal_path(self):
        assert users_svc.get_user_ssh_path("rahat") == "/home/rahat/.ssh/authorized_keys"


class TestGetSshKeys:
    def test_parses_keys_and_skips_comments(self):
        content = (
            "# comment line\n"
            "ssh-rsa AAAAB3NzaC1yc2EAAAKEYDATA rahat@phone\n"
            "ecdsa-sha2-nistp256 AAAAE2VjZHNhKEYDATA laptop\n"
        )
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=content)):
            keys = users_svc.get_user_ssh_keys("rahat")
        assert len(keys) == 2
        assert keys[0]["type"] == "ssh-rsa"
        assert keys[0]["comment"] == "rahat@phone"
        assert keys[1]["type"] == "ecdsa-sha2-nistp256"
        assert keys[1]["comment"] == "laptop"

    def test_missing_file_returns_empty(self):
        with patch("os.path.exists", return_value=False):
            assert users_svc.get_user_ssh_keys("rahat") == []


class TestAddSshKey:
    def test_valid_key_succeeds(self):
        with patch("os.makedirs"), \
             patch("builtins.open", mock_open()), \
             patch("os.chmod"):
            assert users_svc.add_user_ssh_key("rahat", "ssh-rsa AAAA test") is True

    def test_invalid_key_rejected(self):
        assert users_svc.add_user_ssh_key("rahat", "not-a-key") is False


class TestDeleteSshKey:
    def test_removes_line_at_index(self):
        m = mock_open()
        m.return_value.readlines.return_value = ["key1\n", "key2\n", "key3\n"]
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", m):
            assert users_svc.delete_user_ssh_key("rahat", 1) is True
        written = m.return_value.writelines.call_args[0][0]
        assert written == ["key1\n", "key3\n"]

    def test_out_of_range_returns_false(self):
        with patch("os.path.exists", return_value=False):
            assert users_svc.delete_user_ssh_key("rahat", 0) is False


class TestHomeStorageInfo:
    def test_returns_storage(self):
        total, used, free = 48_000_000_000, 20_000_000_000, 28_000_000_000
        with patch("os.path.isdir", return_value=True), \
             patch("dashboard.services.users.shutil.disk_usage",
                   return_value=(total, used, free)):
            info = users_svc.get_home_storage_info("/home/rahat")
        assert info["total_gb"] == round(total / (1024 ** 3), 1)
        assert info["percent_used"] == round((used / total) * 100, 1)

    def test_not_a_dir_returns_none(self):
        with patch("os.path.isdir", return_value=False):
            assert users_svc.get_home_storage_info("/nonexistent") is None


class TestGetHumanUsers:
    def test_enriches_user(self):
        raw_users = [
            {"name": "rahat", "uid": 1000, "gid": 1000,
             "home": "/home/rahat", "shell": "/bin/bash", "comment": "Rahat"},
        ]
        groups = [{"name": "wheel", "gid": 0, "members": ["rahat"]}]
        sessions = [{"user": "rahat", "tty": "tty1", "host": "Local",
                     "login_time": "x", "idle": "Active"}]
        with patch("dashboard.services.users.parse_passwd_users", return_value=raw_users), \
             patch("dashboard.services.users.parse_groups", return_value=groups), \
             patch("dashboard.services.users.parse_active_sessions", return_value=sessions), \
             patch("os.path.isdir", return_value=True), \
             patch("dashboard.services.users.get_home_storage_info", return_value={"total_gb": 1.0}), \
             patch("dashboard.services.users.get_user_ssh_keys", return_value=[]):
            result = users_svc.get_human_users("rahat")
        assert len(result) == 1
        u = result[0]
        assert u["name"] == "rahat"
        assert u["is_admin"] is True  # member of wheel
        assert u["is_current"] is True
        assert u["is_active"] is True
        assert u["groups"] == ["wheel"]


class TestGetSystemUsers:
    def test_only_non_human(self):
        all_users = [
            {"name": "root", "uid": 0, "gid": 0, "home": "/root",
             "shell": "/bin/bash", "comment": "", "is_human": True},
            {"name": "caddy", "uid": 999, "gid": 999, "home": "/nonexistent",
             "shell": "/sbin/nologin", "comment": "", "is_human": False},
        ]
        groups = [{"name": "caddy", "gid": 999, "members": []}]
        with patch("dashboard.services.users.parse_all_passwd_users", return_value=all_users), \
             patch("dashboard.services.users.parse_groups", return_value=groups):
            sys_users = users_svc.get_system_users()
        assert [u["name"] for u in sys_users] == ["caddy"]


class TestCategorizedGroups:
    def test_categorizes_and_orders(self):
        groups = [
            {"name": "sudo", "gid": 27, "members": ["rahat"]},
            {"name": "audio", "gid": 29, "members": []},
            {"name": "caddy", "gid": 1000, "members": []},
            {"name": "random", "gid": 1000, "members": []},
            {"name": "bin", "gid": 1, "members": []},
        ]
        with patch("dashboard.services.users.parse_groups", return_value=groups):
            categorized = users_svc.get_categorized_groups()
        by_name = {g["name"]: g for g in categorized}
        assert by_name["sudo"]["category"] == "Privileged"
        assert by_name["audio"]["category"] == "Hardware"
        assert by_name["caddy"]["category"] == "Services"
        assert by_name["random"]["category"] == "General"
        assert by_name["bin"]["category"] == "System"
        # Privileged sorts first
        assert categorized[0]["name"] == "sudo"


class TestGetUserGroups:
    def test_returns_membership(self):
        groups = [
            {"name": "wheel", "gid": 0, "members": ["rahat"]},
            {"name": "audio", "gid": 29, "members": ["other"]},
        ]
        with patch("dashboard.services.users.parse_groups", return_value=groups):
            assert users_svc.get_user_groups("rahat") == ["wheel"]


class TestSecurityPosture:
    def test_detects_sudo_and_sshd(self):
        with patch("dashboard.services.users.which",
                   side_effect=lambda p: "/usr/bin/sudo" if p == "sudo" else None), \
             patch("dashboard.services.users.visudo_check", return_value=(True, "OK")), \
             patch("dashboard.services.users.run_command", return_value=(0, "active", "")), \
             patch("os.path.isfile", return_value=False):
            posture = users_svc.get_security_posture()
        assert posture["elevation_engine"] == "sudo"
        assert posture["has_sudo"] is True
        assert posture["has_doas"] is False
        assert posture["sshd_active"] is True
        assert posture["root_ssh_login"] == "Unknown"


class TestSudoersInfo:
    def test_returns_content_and_visudo(self):
        with patch("dashboard.services.users.read_sudoers",
                   return_value="root ALL=(ALL) ALL"), \
             patch("dashboard.services.users.visudo_check", return_value=(True, "OK")):
            info = users_svc.get_sudoers_info()
        assert info["sudoers_available"] is True
        assert info["sudoers_content"] == "root ALL=(ALL) ALL"
        assert info["visudo_ok"] is True


class TestWrappers:
    def test_get_users(self):
        with patch("dashboard.services.users.parse_passwd_users",
                   return_value=[{"name": "rahat"}]):
            assert users_svc.get_users() == [{"name": "rahat"}]

    def test_get_current_user(self):
        with patch("dashboard.services.users.get_current_user_info",
                   return_value={"uid": 1000}):
            assert users_svc.get_current_user() == {"uid": 1000}
