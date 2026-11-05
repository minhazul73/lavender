from unittest.mock import patch

from server.services.packages import DnfManager


class TestDnfManager:
    def test_commands(self):
        mgr = DnfManager()
        assert mgr.get_install_command("htop") == ["dnf", "install", "-y", "htop"]
        assert mgr.get_remove_command("htop") == ["dnf", "remove", "-y", "htop"]
        assert mgr.get_upgrade_command() == ["dnf", "upgrade", "-y"]

    @patch("server.services.packages.run_command")
    def test_get_installed_packages(self, mock_run):
        mock_run.return_value = (0, "htop\t3.3.0-1\tx86_64\n", "")
        pkgs = DnfManager().get_installed_packages()
        assert len(pkgs) == 1
        assert pkgs[0]["name"] == "htop"
        assert pkgs[0]["arch"] == "x86_64"

    @patch("server.services.packages.run_command")
    def test_get_upgradable_packages_exit_100(self, mock_run):
        mock_run.return_value = (100, "htop 3.3.0-1\n", "")
        pkgs = DnfManager().get_upgradable_packages()
        assert len(pkgs) == 1

    @patch("server.services.packages.run_command")
    def test_get_upgradable_packages_exit_0(self, mock_run):
        mock_run.return_value = (0, "", "")
        assert DnfManager().get_upgradable_packages() == []

    @patch("server.services.packages.run_command")
    def test_get_upgradable_packages_error(self, mock_run):
        mock_run.return_value = (1, "", "err")
        assert DnfManager().get_upgradable_packages() == []

    @patch("server.services.packages.run_command")
    def test_search_packages(self, mock_run):
        mock_run.return_value = (0, "htop : Interactive process viewer\n", "")
        results = DnfManager().search_packages("htop")
        assert len(results) == 1
        assert results[0]["name"] == "htop"
        assert "Interactive" in results[0]["description"]
