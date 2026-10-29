"""Tests for BasePackageManager and NullPackageManager."""

from dashboard.services.packages import (
    BasePackageManager,
    NullPackageManager,
)


class TestBasePackageManager:
    def test_defaults(self):
        mgr = BasePackageManager()
        assert mgr.id == "generic"
        assert mgr.is_available() is False
        assert mgr.get_installed_packages() == []
        assert mgr.get_installed_count() == 0
        assert mgr.get_upgradable_packages() == []
        assert mgr.search_packages("x") == []
        assert mgr.get_package_info("x")["package"] == "x"
        assert mgr.get_upgrade_command() == []
        assert mgr.get_install_command("x") == []
        assert mgr.get_remove_command("x") == []


class TestNullPackageManager:
    def test_attributes(self):
        mgr = NullPackageManager()
        assert mgr.id == "none"
        assert mgr.is_available() is False
