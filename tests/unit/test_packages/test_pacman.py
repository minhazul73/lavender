"""Tests for PacmanManager."""

from dashboard.services.packages import PacmanManager


class TestPacmanManager:
    def test_id_attribute(self):
        mgr = PacmanManager()
        assert mgr.id == "pacman"

    def test_commands(self):
        mgr = PacmanManager()
        assert mgr.get_install_command("htop") == [
            "pacman",
            "-S",
            "--noconfirm",
            "htop",
        ]
        assert mgr.get_remove_command("htop") == ["pacman", "-R", "--noconfirm", "htop"]
        assert mgr.get_upgrade_command() == ["pacman", "-Syu", "--noconfirm"]

    def test_is_available_when_pacman_exists(self, mock_path_exists):
        mock_path_exists.return_value = True
        mgr = PacmanManager()
        assert mgr.is_available() is True

    def test_is_available_when_pacman_missing(self, mock_path_exists):
        mock_path_exists.return_value = False
        mgr = PacmanManager()
        assert mgr.is_available() is False

    def test_get_installed_packages(
        self, mock_run_command, pacman_installed_packages_output
    ):
        mock_run_command.return_value = pacman_installed_packages_output
        mgr = PacmanManager()
        pkgs = mgr.get_installed_packages()

        assert len(pkgs) == 2
        assert pkgs[0]["name"] == "htop"
        assert pkgs[0]["version"] == "3.3.0-1"
        assert pkgs[1]["name"] == "vim"
        assert pkgs[1]["version"] == "9.0-1"

    def test_get_installed_packages_fail(self, mock_run_command):
        mock_run_command.return_value = (1, "", "err")
        mgr = PacmanManager()
        pkgs = mgr.get_installed_packages()
        assert pkgs == []

    def test_get_upgradable_packages(self, mock_run_command):
        mock_run_command.return_value = (0, "htop 3.2.0-1 -> 3.3.0-1\n", "")
        mgr = PacmanManager()
        pkgs = mgr.get_upgradable_packages()
        assert len(pkgs) == 1
        assert pkgs[0]["current_version"] == "3.2.0-1"
        assert pkgs[0]["version"] == "3.3.0-1"

    def test_get_upgradable_packages_fail(self, mock_run_command):
        mock_run_command.return_value = (1, "", "err")
        pkgs = PacmanManager().get_upgradable_packages()
        assert pkgs == []

    def test_get_upgradable_uses_checkupdates(self, mock_run_command, mock_path_exists):
        mock_path_exists.return_value = "/usr/bin/checkupdates"
        mock_run_command.return_value = (0, "", "")
        mgr = PacmanManager()
        mgr.get_upgradable_packages()
        mock_run_command.assert_called_once_with(["/usr/bin/checkupdates"], timeout=25)

    def test_get_upgradable_uses_pacman_when_checkupdates_missing(
        self, mock_run_command, mock_path_exists
    ):
        mock_path_exists.return_value = None
        mock_run_command.return_value = (0, "htop 3.2.0-1 -> 3.3.0-1\n", "")
        mgr = PacmanManager()
        mgr.get_upgradable_packages()
        mock_run_command.assert_called_once_with(["pacman", "-Qu"], timeout=25)

    def test_search_packages(self, mock_run_command):
        out = "core/htop 3.3.0-1\n    Interactive process viewer\n"
        mock_run_command.return_value = (0, out, "")
        results = PacmanManager().search_packages("htop")
        assert len(results) == 1
        assert results[0]["name"] == "htop"
        assert "Interactive" in results[0]["description"]

    def test_search_packages_empty_results(self, mock_run_command):
        mock_run_command.return_value = (0, "", "")
        results = PacmanManager().search_packages("htop")
        assert results == []

    def test_search_packages_fail(self, mock_run_command):
        mock_run_command.return_value = (1, "", "err")
        results = PacmanManager().search_packages("htop")
        assert len(results) == 1
        assert results[0]["error"] == "err"

    def test_get_installed_packages_handles_malformed_output(self, mock_run_command):
        """Test parsing when output doesn't match expected format."""
        mock_run_command.return_value = (
            0,
            "invalid-line-no-space\nanother-bad-line\n",
            "",
        )
        mgr = PacmanManager()
        pkgs = mgr.get_installed_packages()
        # Should handle gracefully, not crash
        assert isinstance(pkgs, list)

    def test_get_installed_packages_handles_empty_output(self, mock_run_command):
        """Test parsing when output is empty."""
        mock_run_command.return_value = (0, "", "")
        mgr = PacmanManager()
        pkgs = mgr.get_installed_packages()
        assert pkgs == []
