from unittest.mock import MagicMock, patch

from server.utils.subprocess import run_command, run_sudo_command


def test_run_command_success():
    with patch("server.utils.subprocess.get_executor") as mock_get_executor:
        mock_executor = MagicMock()
        mock_result = MagicMock(returncode=0, stdout="output\n", stderr="")
        mock_executor.run_sync.return_value = mock_result
        mock_get_executor.return_value = mock_executor

        code, out, err = run_command(["echo", "hello"], timeout=15)

        assert code == 0
        assert out == "output\n"
        assert err == ""
        mock_executor.run_sync.assert_called_once_with(["echo", "hello"], timeout=15.0)


def test_run_sudo_command_prepends_sudo_n():
    with patch("server.utils.subprocess.get_executor") as mock_get_executor:
        mock_executor = MagicMock()
        mock_result = MagicMock(returncode=0, stdout="ok", stderr="")
        mock_executor.run_sync.return_value = mock_result
        mock_get_executor.return_value = mock_executor

        code, out, err = run_sudo_command(["systemctl", "restart", "foo"])

        assert code == 0
        mock_executor.run_sync.assert_called_once_with(["sudo", "-n", "systemctl", "restart", "foo"], timeout=30.0)


def test_run_sudo_command_preserves_existing_n_flag():
    with patch("server.utils.subprocess.get_executor") as mock_get_executor:
        mock_executor = MagicMock()
        mock_result = MagicMock(returncode=0, stdout="ok", stderr="")
        mock_executor.run_sync.return_value = mock_result
        mock_get_executor.return_value = mock_executor

        code, out, err = run_sudo_command(["-n", "systemctl", "status", "foo"], timeout=10)

        assert code == 0
        mock_executor.run_sync.assert_called_once_with(["sudo", "-n", "systemctl", "status", "foo"], timeout=10.0)
