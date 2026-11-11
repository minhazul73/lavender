import time
from unittest.mock import MagicMock, patch

from server.services.packages import (
    _PACKAGES_CACHE,
    NullPackageManager,
    get_installed_count,
    get_installed_packages,
    install_package,
    invalidate_packages_cache,
    remove_package,
    search_packages,
    upgrade_packages,
)


class TestCacheAndWrappers:
    def setup_method(self):
        invalidate_packages_cache()
        import server.services.packages as pkgs
        pkgs._CURRENT_MANAGER = None

    def test_invalidate_cache(self):
        _PACKAGES_CACHE["installed"] = [{"name": "x"}]
        _PACKAGES_CACHE["timestamp"] = time.time()
        invalidate_packages_cache()
        assert _PACKAGES_CACHE["installed"] is None
        assert _PACKAGES_CACHE["timestamp"] == 0.0

    @patch("server.services.packages.get_package_manager")
    def test_get_installed_packages_caching(self, mock_get_mgr):
        mock_mgr = MagicMock()
        mock_mgr.get_installed_packages.return_value = [{"name": "htop"}]
        mock_get_mgr.return_value = mock_mgr

        result1 = get_installed_packages()
        result2 = get_installed_packages()
        assert result1 == result2
        mock_mgr.get_installed_packages.assert_called_once()

    @patch("server.services.packages.get_package_manager")
    def test_get_installed_packages_force_refresh(self, mock_get_mgr):
        cache_during_call = []

        def side_effect():
            cache_during_call.append(_PACKAGES_CACHE["installed"])
            return [{"name": "htop"}]

        mock_mgr = MagicMock()
        mock_mgr.get_installed_packages.side_effect = side_effect
        mock_get_mgr.return_value = mock_mgr

        _PACKAGES_CACHE["installed"] = [{"name": "old"}]
        _PACKAGES_CACHE["timestamp"] = time.time()

        res = get_installed_packages(force_refresh=True)
        mock_mgr.get_installed_packages.assert_called_once()
        assert cache_during_call == [None]  # Cleared prior to allocation
        assert res == [{"name": "htop"}]
        assert _PACKAGES_CACHE["installed"] == [{"name": "htop"}]

    @patch("server.services.packages.get_package_manager")
    def test_get_installed_count_from_cache(self, mock_get_mgr):
        _PACKAGES_CACHE["installed"] = [{"name": "a"}, {"name": "b"}]
        assert get_installed_count() == 2
        mock_get_mgr.assert_not_called()

    @patch("server.services.packages.get_package_manager")
    def test_search_packages_empty_query(self, mock_get_mgr):
        assert search_packages("") == []
        assert search_packages("   ") == []
        mock_get_mgr.assert_not_called()

    @patch("server.services.packages.run_sudo_command")
    @patch("server.services.packages.get_package_manager")
    def test_upgrade_packages_no_cmd(self, mock_get_mgr, mock_sudo):
        mock_get_mgr.return_value = NullPackageManager()
        res = upgrade_packages()
        assert res["success"] is False
        assert "No upgrade command" in res["error"]

    @patch("server.services.packages.run_sudo_command")
    @patch("server.services.packages.get_package_manager")
    def test_install_package_success(self, mock_get_mgr, mock_sudo):
        mock_mgr = MagicMock()
        mock_mgr.get_install_command.return_value = ["apk", "add", "htop"]
        mock_get_mgr.return_value = mock_mgr
        mock_sudo.return_value = (0, "OK", "")
        res = install_package("htop")
        assert res["success"] is True

    @patch("server.services.packages.run_sudo_command")
    @patch("server.services.packages.get_package_manager")
    def test_remove_package_failure(self, mock_get_mgr, mock_sudo):
        mock_mgr = MagicMock()
        mock_mgr.get_remove_command.return_value = ["apk", "del", "htop"]
        mock_get_mgr.return_value = mock_mgr
        mock_sudo.return_value = (1, "", "permission denied")
        res = remove_package("htop")
        assert res["success"] is False
        assert res["error"] == "permission denied"
