from unittest.mock import patch

from server.services.packages import PacmanManager


class TestPacmanManager:
    def test_commands(self):
        mgr = PacmanManager()
        assert mgr.get_install_command("htop") == ["pacman", "-S", "--noconfirm", "htop"]
        assert mgr.get_remove_command("htop") == ["pacman", "-R", "--noconfirm", "htop"]
        assert mgr.get_upgrade_command() == ["pacman", "-Syu", "--noconfirm"]

    @patch("server.services.packages.run_command")
    def test_get_installed_packages(self, mock_run):
        mock_run.return_value = (0, "htop 3.3.0-1\nvim 9.0-1\n", "")
        pkgs = PacmanManager().get_installed_packages()
        assert len(pkgs) == 2
        assert pkgs[0]["name"] == "htop"
        assert pkgs[0]["version"] == "3.3.0-1"

    @patch("server.services.packages.run_command")
    def test_get_upgradable_packages(self, mock_run):
        mock_run.return_value = (0, "htop 3.2.0-1 -> 3.3.0-1\n", "")
        pkgs = PacmanManager().get_upgradable_packages()
        assert len(pkgs) == 1
        assert pkgs[0]["current_version"] == "3.2.0-1"
        assert pkgs[0]["version"] == "3.3.0-1"

    @patch("server.services.packages.shutil.which")
    @patch("server.services.packages.run_command")
    def test_get_upgradable_uses_checkupdates(self, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/checkupdates"
        mock_run.return_value = (0, "", "")
        PacmanManager().get_upgradable_packages()
        mock_run.assert_called_once_with(["/usr/bin/checkupdates"], timeout=25)

    @patch("server.services.packages.run_command")
    def test_search_packages(self, mock_run):
        out = "core/htop 3.3.0-1\n    Interactive process viewer\n"
        mock_run.return_value = (0, out, "")
        results = PacmanManager().search_packages("htop")
        assert len(results) == 1
        assert results[0]["name"] == "htop"
        assert "Interactive" in results[0]["description"]
