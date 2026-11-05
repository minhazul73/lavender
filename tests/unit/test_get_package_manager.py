from unittest.mock import patch

from server.services.packages import ApkManager, AptManager, get_package_manager


class TestGetPackageManager:
    def setup_method(self):
        import server.services.packages as pkgs
        pkgs._CURRENT_MANAGER = None

    @patch("server.services.packages.shutil.which")
    def test_detects_apk(self, mock_which):
        mock_which.side_effect = lambda x: "/sbin/apk" if x == "apk" else None
        mgr = get_package_manager()
        assert isinstance(mgr, ApkManager)

    @patch("server.services.packages.shutil.which")
    def test_detects_apt(self, mock_which):
        mock_which.side_effect = lambda x: (
            "/usr/bin/dpkg-query" if x == "dpkg-query" else None
        )
        mgr = get_package_manager()
        assert isinstance(mgr, AptManager)

    @patch("server.services.packages.shutil.which")
    def test_caches_manager(self, mock_which):
        mock_which.side_effect = lambda x: "/sbin/apk" if x == "apk" else None
        m1 = get_package_manager()
        m2 = get_package_manager()
        assert m1 is m2
