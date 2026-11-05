from server.services.packages import BasePackageManager, NullPackageManager


def test_defaults():
    """Test BasePackageManager default implementations."""
    manager = BasePackageManager()
    assert manager.id == "generic"
    assert manager.name == "Generic Package Manager"
    assert manager.short_name == "Package Manager"
    assert manager.is_available() is False
    assert manager.get_installed_packages() == []
    assert manager.get_installed_count() == 0
    assert manager.get_upgradable_packages() == []
    assert manager.search_packages("x") == []
    assert manager.get_package_info("x")["package"] == "x"
    assert manager.get_upgrade_command() == []
    assert manager.get_install_command("x") == []
    assert manager.get_remove_command("x") == []


def test_attributes():
    """Test NullPackageManager attributes."""
    manager = NullPackageManager()
    assert manager.id == "none"
    assert manager.name == "No Package Manager Detected"
    assert manager.short_name == "none"
    assert manager.is_available() is False
