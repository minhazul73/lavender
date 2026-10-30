import asyncio
import subprocess
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from dashboard.auth.bridge import (
    AuthError,
    authenticate_user,
    drop_sudo_ticket,
    get_local_user_info,
    run_command_async,
    run_sudo_async,
    run_user_service_async,
    verify_linux_credentials,
    verify_sudo_password,
)


def _make_proc(returncode: int = 0, stdout: bytes = b"", stderr: bytes = b""):
    """Build a mock asyncio subprocess with awaitable communicate/wait."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.wait = AsyncMock(return_value=returncode)
    return proc


class TestGetLocalUserInfo(unittest.TestCase):
    @patch("grp.getgrgid")
    @patch("grp.getgrall")
    @patch("pwd.getpwnam")
    def test_success(self, mock_pwnam, mock_grall, mock_grgid):
        pw = MagicMock()
        pw.pw_uid = 1000
        pw.pw_gid = 1000
        pw.pw_dir = "/home/testuser"
        pw.pw_shell = "/bin/bash"
        mock_pwnam.return_value = pw

        grp1 = MagicMock()
        grp1.gr_name = "testgroup"
        grp1.gr_mem = ["testuser"]
        mock_grall.return_value = [grp1]

        primary = MagicMock()
        primary.gr_name = "primarygroup"
        mock_grgid.return_value = primary

        result = get_local_user_info("testuser")
        self.assertEqual(result["uid"], 1000)
        self.assertEqual(result["gid"], 1000)
        self.assertEqual(result["home"], "/home/testuser")
        self.assertEqual(result["shell"], "/bin/bash")
        # Primary group prepended, supplemental group kept
        self.assertEqual(result["groups"], ["primarygroup", "testgroup"])

    @patch("pwd.getpwnam")
    def test_unknown_user_raises(self, mock_pwnam):
        mock_pwnam.side_effect = KeyError("no such user")
        with self.assertRaises(AuthError) as ctx:
            get_local_user_info("ghost")
        self.assertIn("ghost", str(ctx.exception))

    @patch("grp.getgrgid")
    @patch("grp.getgrall")
    @patch("pwd.getpwnam")
    def test_primary_group_lookup_failure_is_nonfatal(
        self, mock_pwnam, mock_grall, mock_grgid
    ):
        pw = MagicMock()
        pw.pw_uid = 1000
        pw.pw_gid = 1000
        pw.pw_dir = "/home/testuser"
        pw.pw_shell = "/bin/bash"
        mock_pwnam.return_value = pw
        mock_grall.return_value = []
        mock_grgid.side_effect = KeyError("no such group")

        result = get_local_user_info("testuser")
        self.assertEqual(result["groups"], [])
        self.assertEqual(result["uid"], 1000)

    @patch("grp.getgrgid")
    @patch("grp.getgrall")
    @patch("pwd.getpwnam")
    def test_primary_group_not_duplicated(self, mock_pwnam, mock_grall, mock_grgid):
        """Primary group already in the supplemental list must not be
        inserted a second time."""
        pw = MagicMock()
        pw.pw_uid = 1000
        pw.pw_gid = 1000
        pw.pw_dir = "/home/testuser"
        pw.pw_shell = "/bin/bash"
        mock_pwnam.return_value = pw

        grp1 = MagicMock()
        grp1.gr_name = "primarygroup"
        grp1.gr_mem = ["testuser"]
        mock_grall.return_value = [grp1]

        primary = MagicMock()
        primary.gr_name = "primarygroup"  # same name as supplemental
        mock_grgid.return_value = primary

        result = get_local_user_info("testuser")
        self.assertEqual(result["groups"], ["primarygroup"])


class TestVerifyLinuxCredentials(unittest.TestCase):
    """verify_linux_credentials is synchronous; all external I/O is mocked."""

    def test_empty_password_rejected(self):
        with patch("subprocess.run") as mock_run:
            self.assertFalse(verify_linux_credentials("testuser", ""))
            mock_run.assert_not_called()

    @patch.dict("sys.modules")
    def test_shadow_success(self):
        sp = MagicMock()
        sp.sp_pwdp = "hash"
        spwd = MagicMock()
        spwd.getspnam.return_value = sp
        crypt = MagicMock()
        crypt.crypt.return_value = "hash"
        with patch.dict("sys.modules", {"spwd": spwd, "crypt": crypt}), patch(
            "subprocess.run"
        ) as mock_run:
            self.assertTrue(verify_linux_credentials("testuser", "right"))
            # Shadow hit short-circuits before sudo
            mock_run.assert_not_called()

    @patch.dict("sys.modules")
    def test_shadow_mismatch_falls_through_to_sudo(self):
        """Hash mismatch must not stop the chain; sudo -v then succeeds."""
        sp = MagicMock()
        sp.sp_pwdp = "hash"
        spwd = MagicMock()
        spwd.getspnam.return_value = sp
        crypt = MagicMock()
        crypt.crypt.return_value = "different"
        with patch.dict("sys.modules", {"spwd": spwd, "crypt": crypt}), patch(
            "subprocess.run"
        ) as mock_run, patch("os.path.isdir", return_value=False), patch(
            "os.path.isfile", return_value=False
        ):
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            self.assertTrue(verify_linux_credentials("testuser", "right"))
            # sudo -k then sudo -S -v
            self.assertGreaterEqual(mock_run.call_count, 2)

    @patch.dict("sys.modules")
    def test_spwd_module_unavailable_falls_through(self):
        """spwd not importable (common on musl) — import error swallowed,
        chain continues to sudo."""
        with patch.dict("sys.modules", {"spwd": None, "crypt": None}), patch(
            "subprocess.run"
        ) as mock_run, patch("os.path.isfile", return_value=False):
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            self.assertTrue(verify_linux_credentials("testuser", "right"))

    @patch.dict("sys.modules")
    def test_pam_success(self):
        """Shadow unavailable; PAM authenticates."""
        pam_mod = MagicMock()
        inst = MagicMock()
        inst.authenticate.return_value = True
        pam_mod.pam.return_value = inst
        with patch.dict(
            "sys.modules", {"spwd": None, "crypt": None, "pam": pam_mod}
        ), patch("subprocess.run") as mock_run:
            self.assertTrue(verify_linux_credentials("testuser", "right"))
            # PAM hit short-circuits before sudo
            mock_run.assert_not_called()

    @patch.dict("sys.modules")
    def test_pam_failure_falls_through_to_sudo(self):
        """PAM rejects; sudo -v accepts."""
        pam_mod = MagicMock()
        inst = MagicMock()
        inst.authenticate.return_value = False
        inst.code = -1
        inst.reason = "auth err"
        pam_mod.pam.return_value = inst
        with patch.dict(
            "sys.modules", {"spwd": None, "crypt": None, "pam": pam_mod}
        ), patch("subprocess.run") as mock_run, patch(
            "os.path.isdir", return_value=False
        ), patch(
            "os.path.isfile", return_value=False
        ):
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            self.assertTrue(verify_linux_credentials("testuser", "right"))

    @patch.dict("sys.modules")
    def test_sudo_timeout_is_handled(self):
        """A hanging sudo must not crash the except clause — before the
        fix this raised AttributeError (asyncio.TimeoutExpired does not
        exist on Python 3.11+); it must return False instead."""
        pam_mod = MagicMock()
        inst = MagicMock()
        inst.authenticate.side_effect = Exception("pam unavailable")
        pam_mod.pam.return_value = inst
        with patch.dict(
            "sys.modules", {"spwd": None, "crypt": None, "pam": pam_mod}
        ), patch("subprocess.run") as mock_run, patch(
            "os.path.isdir", return_value=False
        ), patch(
            "os.path.isfile", return_value=False
        ):
            mock_run.side_effect = [
                subprocess.TimeoutExpired(cmd="sudo -k", timeout=2),
                subprocess.TimeoutExpired(cmd="sudo -v", timeout=5),
            ]
            self.assertFalse(verify_linux_credentials("testuser", "pw"))

    @patch.dict("sys.modules")
    def test_all_methods_fail_returns_false(self):
        """Every auth path fails -> False, no exception escapes."""
        pam_mod = MagicMock()
        inst = MagicMock()
        inst.authenticate.return_value = False
        inst.code = -1
        inst.reason = "auth err"
        pam_mod.pam.return_value = inst
        with patch.dict(
            "sys.modules", {"spwd": None, "crypt": None, "pam": pam_mod}
        ), patch("subprocess.run") as mock_run, patch(
            "os.path.isdir", return_value=False
        ), patch(
            "os.path.isfile", return_value=False
        ):
            mock_run.return_value = MagicMock(returncode=1, stderr="bad creds")
            self.assertFalse(verify_linux_credentials("testuser", "wrong"))


class TestAuthenticateUser(unittest.IsolatedAsyncioTestCase):
    @patch("dashboard.auth.bridge.verify_linux_credentials")
    @patch("dashboard.auth.bridge.get_local_user_info")
    async def test_success(self, mock_info, mock_verify):
        mock_info.return_value = {
            "uid": 1000,
            "gid": 1000,
            "groups": ["users"],
            "home": "/home/testuser",
            "shell": "/bin/bash",
        }
        mock_verify.return_value = True
        result = await authenticate_user("testuser", "right")
        self.assertEqual(result["uid"], 1000)
        mock_verify.assert_called_once_with("testuser", "right")

    @patch("dashboard.auth.bridge.verify_linux_credentials")
    @patch("dashboard.auth.bridge.get_local_user_info")
    async def test_bad_credentials_raise_auth_error(self, mock_info, mock_verify):
        mock_info.return_value = {
            "uid": 1000,
            "gid": 1000,
            "groups": [],
            "home": "/home/testuser",
            "shell": "/bin/bash",
        }
        mock_verify.return_value = False
        with self.assertRaises(AuthError) as ctx:
            await authenticate_user("testuser", "wrong")
        self.assertIn("Invalid", str(ctx.exception))

    @patch("dashboard.auth.bridge.get_local_user_info")
    async def test_unknown_user_raises_before_verify(self, mock_info):
        mock_info.side_effect = AuthError("User 'ghost' does not exist")
        with self.assertRaises(AuthError):
            await authenticate_user("ghost", "pw")


class TestRunCommandAsync(unittest.IsolatedAsyncioTestCase):
    @patch("asyncio.create_subprocess_shell")
    async def test_shell_string_success(self, mock_create):
        mock_create.return_value = _make_proc(0, b"hello\n", b"")
        code, out, err = await run_command_async("echo hello")
        self.assertEqual(code, 0)
        self.assertEqual(out, "hello")
        self.assertEqual(err, "")
        args, kwargs = mock_create.call_args
        self.assertEqual(args, ("echo hello",))
        self.assertEqual(kwargs["stdout"], asyncio.subprocess.PIPE)

    @patch("asyncio.create_subprocess_exec")
    async def test_exec_list_nonzero_exit(self, mock_create):
        mock_create.return_value = _make_proc(2, b"", b"boom")
        code, out, err = await run_command_async(["/bin/false", "arg"])
        self.assertEqual(code, 2)
        self.assertEqual(err, "boom")
        args, _ = mock_create.call_args
        self.assertEqual(args, ("/bin/false", "arg"))

    @patch("asyncio.create_subprocess_shell")
    async def test_spawn_failure_returns_error_tuple(self, mock_create):
        mock_create.side_effect = OSError("spawn failed")
        code, out, err = await run_command_async("nope")
        self.assertEqual(code, -1)
        self.assertEqual(err, "spawn failed")

    @patch("asyncio.create_subprocess_shell")
    async def test_timeout_kills_and_reports(self, mock_create):
        proc = _make_proc(0)
        proc.communicate = AsyncMock(side_effect=TimeoutError)
        mock_create.return_value = proc
        code, out, err = await run_command_async("sleep 100", timeout=0.01)
        self.assertEqual(code, -1)
        self.assertEqual(err, "Command timed out")
        proc.kill.assert_called_once()


class TestRunUserServiceAsync(unittest.IsolatedAsyncioTestCase):
    @patch("asyncio.create_subprocess_exec")
    async def test_success_sets_xdg_env(self, mock_create):
        mock_create.return_value = _make_proc(0, b"active", b"")
        code, out, err = await run_user_service_async(
            1000, ["systemctl", "--user", "is-active", "foo"]
        )
        self.assertEqual(code, 0)
        self.assertEqual(out, "active")
        _, kwargs = mock_create.call_args
        self.assertEqual(kwargs["env"]["XDG_RUNTIME_DIR"], "/run/user/1000")
        self.assertEqual(
            kwargs["env"]["DBUS_SESSION_BUS_ADDRESS"],
            "unix:path=/run/user/1000/systemd/private",
        )

    @patch("asyncio.create_subprocess_exec")
    async def test_spawn_failure_returns_error_tuple(self, mock_create):
        mock_create.side_effect = OSError("no such user session")
        code, out, err = await run_user_service_async(1000, ["systemctl"])
        self.assertEqual(code, -1)
        self.assertEqual(err, "no such user session")

    @patch("asyncio.create_subprocess_exec")
    async def test_timeout_kills_and_reports(self, mock_create):
        proc = _make_proc(0)
        proc.communicate = AsyncMock(side_effect=TimeoutError)
        mock_create.return_value = proc
        code, out, err = await run_user_service_async(1000, ["systemctl"], timeout=0.01)
        self.assertEqual(code, -1)
        self.assertEqual(err, "Command timed out")
        proc.kill.assert_called_once()


class TestVerifySudoPassword(unittest.IsolatedAsyncioTestCase):
    @patch("asyncio.create_subprocess_exec")
    async def test_valid_password(self, mock_create):
        mock_create.return_value = _make_proc(0)
        ok, msg = await verify_sudo_password("right")
        self.assertTrue(ok)
        self.assertEqual(msg, "")
        args, kwargs = mock_create.call_args
        self.assertEqual(args, ("sudo", "-S", "-p", "", "-v"))
        self.assertEqual(kwargs["stdin"], asyncio.subprocess.PIPE)

    @patch("asyncio.create_subprocess_exec")
    async def test_invalid_password_reports_stderr(self, mock_create):
        mock_create.return_value = _make_proc(1, b"", b"sudo: wrong password")
        ok, msg = await verify_sudo_password("wrong")
        self.assertFalse(ok)
        self.assertIn("wrong password", msg)

    @patch("asyncio.create_subprocess_exec")
    async def test_no_error_output_uses_generic_message(self, mock_create):
        mock_create.return_value = _make_proc(1, b"", b"")
        ok, msg = await verify_sudo_password("wrong")
        self.assertFalse(ok)
        self.assertIn("sudoers", msg)

    @patch("asyncio.create_subprocess_exec")
    async def test_sudo_missing_returns_error(self, mock_create):
        mock_create.side_effect = FileNotFoundError("no sudo")
        ok, msg = await verify_sudo_password("right")
        self.assertFalse(ok)
        self.assertIn("no sudo", msg)


class TestRunSudoAsync(unittest.IsolatedAsyncioTestCase):
    @patch("asyncio.create_subprocess_exec")
    async def test_with_password_uses_sudo_S(self, mock_create):
        mock_create.return_value = _make_proc(0, b"ok", b"")
        code, out, err = await run_sudo_async(["cat", "/etc/shadow"], password="x")
        self.assertEqual(code, 0)
        args, _ = mock_create.call_args
        self.assertEqual(args[:4], ("sudo", "-S", "-p", ""))
        self.assertIn("cat", args)

    @patch("asyncio.create_subprocess_exec")
    async def test_without_password_uses_sudo_n(self, mock_create):
        mock_create.return_value = _make_proc(0, b"ok", b"")
        code, out, err = await run_sudo_async(["id"])
        self.assertEqual(code, 0)
        args, _ = mock_create.call_args
        self.assertEqual(args[:2], ("sudo", "-n"))

    @patch("asyncio.create_subprocess_exec")
    async def test_nonzero_exit_propagates(self, mock_create):
        mock_create.return_value = _make_proc(42, b"", b"permission denied")
        code, out, err = await run_sudo_async(["id"], password="x")
        self.assertEqual(code, 42)
        self.assertEqual(err, "permission denied")

    @patch("asyncio.create_subprocess_exec")
    async def test_spawn_failure_returns_error_tuple(self, mock_create):
        mock_create.side_effect = OSError("spawn failed")
        code, out, err = await run_sudo_async(["id"])
        self.assertEqual(code, -1)
        self.assertEqual(err, "spawn failed")

    @patch("asyncio.create_subprocess_exec")
    async def test_timeout_kills_and_reports(self, mock_create):
        proc = _make_proc(0)
        proc.communicate = AsyncMock(side_effect=TimeoutError)
        mock_create.return_value = proc
        code, out, err = await run_sudo_async(["sleep", "100"], timeout=0.01)
        self.assertEqual(code, -1)
        self.assertEqual(err, "Command timed out")
        proc.kill.assert_called_once()


class TestDropSudoTicket(unittest.IsolatedAsyncioTestCase):
    @patch("asyncio.create_subprocess_exec")
    async def test_runs_sudo_k(self, mock_create):
        mock_create.return_value = _make_proc(0)
        await drop_sudo_ticket()
        args, kwargs = mock_create.call_args
        self.assertEqual(args, ("sudo", "-k"))
        self.assertEqual(kwargs["stdout"], asyncio.subprocess.DEVNULL)
        self.assertEqual(kwargs["stderr"], asyncio.subprocess.DEVNULL)

    @patch("asyncio.create_subprocess_exec")
    async def test_sudo_missing_does_not_raise(self, mock_create):
        mock_create.side_effect = FileNotFoundError("no sudo")
        # Must swallow the failure silently
        await drop_sudo_ticket()


if __name__ == "__main__":
    unittest.main()
