"""
Unit tests for dashboard.dependencies utility functions.
"""
import subprocess
from unittest.mock import patch, MagicMock, mock_open

from dashboard import dependencies as deps


class TestRunCommand:
    @patch("dashboard.dependencies.os.getuid", return_value=1000)
    @patch("dashboard.dependencies.subprocess.run")
    def test_success_strips_output(self, mock_run, _mock_uid):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="hello\n", stderr="world\n"
        )
        code, out, err = deps.run_command(["echo", "hello"])
        assert code == 0
        assert out == "hello"
        assert err == "world"

    @patch("dashboard.dependencies.os.getuid", return_value=1000)
    @patch("dashboard.dependencies.subprocess.run")
    def test_timeout(self, mock_run, _mock_uid):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="x", timeout=5)
        code, out, err = deps.run_command(["x"])
        assert code == -1
        assert out == ""
        assert err == "Command timed out"

    @patch("dashboard.dependencies.os.getuid", return_value=1000)
    @patch("dashboard.dependencies.subprocess.run")
    def test_file_not_found(self, mock_run, _mock_uid):
        mock_run.side_effect = FileNotFoundError
        code, out, err = deps.run_command(["nope"])
        assert code == -1
        assert out == ""
        assert "Command not found: nope" in err

    @patch("dashboard.dependencies.os.getuid", return_value=1000)
    @patch("dashboard.dependencies.subprocess.run")
    def test_generic_error(self, mock_run, _mock_uid):
        mock_run.side_effect = OSError("boom")
        code, out, err = deps.run_command(["boom"])
        assert code == -1
        assert err == "boom"


class TestRunSudoCommand:
    @patch("dashboard.dependencies.os.getuid", return_value=1000)
    @patch("dashboard.dependencies.subprocess.run")
    def test_prepends_sudo(self, mock_run, _mock_uid):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        deps.run_sudo_command(["systemctl", "status"])
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "sudo"
        assert cmd[1:] == ["systemctl", "status"]


class TestWhich:
    @patch("dashboard.dependencies.shutil.which", return_value="/usr/bin/echo")
    def test_found(self, _mock_which):
        assert deps.which("echo") == "/usr/bin/echo"

    @patch("dashboard.dependencies.shutil.which", return_value=None)
    def test_not_found(self, _mock_which):
        assert deps.which("nope") is None


class TestParsePasswdUsers:
    def test_filters_human_users(self):
        passwd = (
            "root:x:0:0:root:/root:/bin/bash\n"
            "rahat:x:1000:1000:Rahat:/home/rahat:/bin/bash\n"
            "nobody:x:65534:65534:nobody:/nonexistent:/sbin/nologin\n"
        )
        with patch("builtins.open", mock_open(read_data=passwd)):
            users = deps.parse_passwd_users()
        names = [u["name"] for u in users]
        assert "rahat" in names
        assert "root" not in names  # uid < 1000
        assert "nobody" not in names  # uid 65534

    def test_exclude_nologin_false_includes_service(self):
        passwd = "svc:x:999:999:svc:/nonexistent:/usr/sbin/nologin\n"
        with patch("builtins.open", mock_open(read_data=passwd)):
            users = deps.parse_passwd_users(min_uid=0, exclude_nologin=False)
        assert [u["name"] for u in users] == ["svc"]

    def test_excludes_nologin_shell(self):
        passwd = "svc:x:2000:2000:svc:/nonexistent:/usr/sbin/nologin\n"
        with patch("builtins.open", mock_open(read_data=passwd)):
            users = deps.parse_passwd_users()
        assert users == []


class TestParseGroups:
    def test_parses_members(self):
        group = (
            "root:x:0:\n"
            "sudo:x:27:rahat\n"
            "audio:x:29:rahat,other\n"
        )
        with patch("builtins.open", mock_open(read_data=group)):
            groups = deps.parse_groups()
        by_name = {g["name"]: g for g in groups}
        assert by_name["sudo"]["members"] == ["rahat"]
        assert by_name["audio"]["members"] == ["rahat", "other"]
        assert by_name["root"]["members"] == []
        assert by_name["audio"]["gid"] == 29


class TestParseActiveSessions:
    @patch("dashboard.dependencies.subprocess.run")
    def test_local_session(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="rahat  tty1  2026-10-26 12:00\n", stderr=""
        )
        sessions = deps.parse_active_sessions()
        assert len(sessions) == 1
        assert sessions[0]["user"] == "rahat"
        assert sessions[0]["tty"] == "tty1"
        assert sessions[0]["host"] == "Local"

    @patch("dashboard.dependencies.subprocess.run")
    def test_remote_session_parses_host(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="rahat  pts/0  2026-10-26 12:00  (192.168.1.5)\n", stderr=""
        )
        sessions = deps.parse_active_sessions()
        assert sessions[0]["host"] == "192.168.1.5"


class TestParseLoginHistory:
    @patch("dashboard.dependencies.subprocess.run")
    def test_filters_reboot_and_wtmp(self, mock_run):
        out = (
            "rahat  pts/0  192.168.1.5  Mon Oct 26 12:00 - 12:30  (00:30)\n"
            "reboot  system boot  5.15.0  Mon Oct 26 11:00   still running\n"
            "wtmp begins Mon Oct 26 10:00:00 2026\n"
        )
        mock_run.return_value = MagicMock(stdout=out, stderr="")
        history = deps.parse_login_history(limit=10)
        assert len(history) == 1
        assert history[0]["user"] == "rahat"
        assert history[0]["tty"] == "pts/0"
        assert history[0]["host"] == "192.168.1.5"


class TestGetCurrentUserInfo:
    @patch("dashboard.dependencies.os.getgid", return_value=1000)
    @patch("dashboard.dependencies.os.getuid", return_value=1000)
    @patch("dashboard.dependencies.subprocess.run")
    def test_returns_uid_gid_and_id(self, mock_run, _uid, _gid):
        mock_run.return_value = MagicMock(stdout="uid=1000(rahat)\n", stderr="")
        info = deps.get_current_user_info()
        assert info["uid"] == 1000
        assert info["gid"] == 1000
        assert "uid=1000(rahat)" in info["id_output"]


class TestReadSudoers:
    def test_returns_content(self):
        with patch("builtins.open", mock_open(read_data="root ALL=(ALL) ALL\n")):
            content = deps.read_sudoers()
        assert content == "root ALL=(ALL) ALL\n"

    def test_missing_returns_empty(self):
        with patch("builtins.open", side_effect=FileNotFoundError):
            content = deps.read_sudoers()
        assert content == ""


class TestVisudoCheck:
    @patch("dashboard.dependencies.run_command")
    def test_ok(self, mock_run):
        mock_run.return_value = (0, "/etc/sudoers: parsed OK", "")
        ok, msg = deps.visudo_check()
        assert ok is True
        assert "parsed OK" in msg

    @patch("dashboard.dependencies.run_command")
    def test_fail_uses_stderr(self, mock_run):
        mock_run.return_value = (1, "", "requires password")
        ok, msg = deps.visudo_check()
        assert ok is False
        assert "requires password" in msg
