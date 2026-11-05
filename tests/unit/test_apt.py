from unittest.mock import patch

from server.services.packages import AptManager


class TestAptManager:
    def test_commands(self):
        mgr = AptManager()
        assert mgr.get_install_command("htop") == [
            "env", "DEBIAN_FRONTEND=noninteractive", "NEEDRESTART_MODE=a",
            "apt-get", "-y", "-o", "Dpkg::Options::=--force-confdef",
            "-o", "Dpkg::Options::=--force-confold", "install", "htop"
        ]
        assert mgr.get_remove_command("htop") == [
            "env", "DEBIAN_FRONTEND=noninteractive", "NEEDRESTART_MODE=a",
            "apt-get", "-y", "-o", "Dpkg::Options::=--force-confdef",
            "-o", "Dpkg::Options::=--force-confold", "remove", "htop"
        ]
        assert mgr.get_upgrade_command() == [
            "env", "DEBIAN_FRONTEND=noninteractive", "NEEDRESTART_MODE=a",
            "apt-get", "-y", "-o", "Dpkg::Options::=--force-confdef",
            "-o", "Dpkg::Options::=--force-confold", "upgrade", "--with-new-pkgs"
        ]
        assert mgr.get_upgrade_command("htop") == [
            "env", "DEBIAN_FRONTEND=noninteractive", "NEEDRESTART_MODE=a",
            "apt-get", "-y", "-o", "Dpkg::Options::=--force-confdef",
            "-o", "Dpkg::Options::=--force-confold", "install", "--only-upgrade", "htop"
        ]

    @patch("server.services.packages.run_command")
    def test_get_installed_packages(self, mock_run):
        mock_run.return_value = (0, "htop\t3.3.0\tamd64\nvim\t9.0\tamd64\n", "")
        pkgs = AptManager().get_installed_packages()
        assert len(pkgs) == 2
        assert pkgs[0]["name"] == "htop"
        assert pkgs[0]["arch"] == "amd64"

    @patch("server.services.packages.run_command")
    def test_get_installed_packages_fail(self, mock_run):
        mock_run.return_value = (1, "", "err")
        assert AptManager().get_installed_packages() == []

    @patch("server.services.packages.run_command")
    def test_get_upgradable_packages(self, mock_run):
        line = "htop/jammy-updates 3.3.0-1 amd64 [upgradable from: 3.2.0-1]"
        mock_run.return_value = (0, f"Listing...\n{line}\n", "")
        pkgs = AptManager().get_upgradable_packages()
        assert len(pkgs) == 1
        assert pkgs[0]["name"] == "htop"
        assert pkgs[0]["current_version"] == "3.2.0-1"

    @patch("server.services.packages.run_command")
    def test_get_upgradable_packages_fail(self, mock_run):
        mock_run.return_value = (1, "", "err")
        pkgs = AptManager().get_upgradable_packages()
        assert "error" in pkgs[0]

    @patch("server.services.packages.run_command")
    def test_search_packages_names_only(self, mock_run):
        mock_run.return_value = (0, "htop - interactive process viewer\n", "")
        results = AptManager().search_packages("htop")
        assert results[0]["name"] == "htop"
        assert "interactive" in results[0]["description"]

    @patch("server.services.packages.run_command")
    def test_search_packages_fallback(self, mock_run):
        mock_run.side_effect = [(0, "", ""), (0, "htop - interactive process viewer\n", "")]
        results = AptManager().search_packages("htop")
        assert len(results) == 1

    @patch("server.services.packages.run_command")
    def test_get_package_info_dpkg(self, mock_run):
        mock_run.return_value = (0, "Package: htop\nVersion: 3.3.0\n", "")
        info = AptManager().get_package_info("htop")
        assert "htop" in info["info"]

    @patch("server.services.packages.run_command")
    def test_get_package_info_fallback_apt_cache(self, mock_run):
        mock_run.side_effect = [(1, "", "not installed"), (0, "Package: htop\n", "")]
        info = AptManager().get_package_info("htop")
        assert "htop" in info["info"]
