"""Parameterized tests for package manager functions."""

import pytest
from dashboard.services.packages import (
    ApkManager,
    AptManager,
    PacmanManager,
    DnfManager,
)


@pytest.mark.parametrize(
    "manager_class,package,expected_install_command",
    [
        pytest.param(ApkManager, "htop", ["apk", "add", "htop"], id="apk_install"),
        pytest.param(
            AptManager, "htop", ["apt-get", "install", "-y", "htop"], id="apt_install"
        ),
        pytest.param(
            PacmanManager,
            "htop",
            ["pacman", "-S", "--noconfirm", "htop"],
            id="pacman_install",
        ),
        pytest.param(
            DnfManager, "htop", ["dnf", "install", "-y", "htop"], id="dnf_install"
        ),
    ],
)
def test_get_install_command(
    manager_class, package, expected_install_command, mock_path_exists
):
    """Test that each package manager generates correct install commands."""
    mock_path_exists.return_value = True
    mgr = manager_class()
    assert mgr.get_install_command(package) == expected_install_command


@pytest.mark.parametrize(
    "manager_class,package,expected_remove_command",
    [
        pytest.param(ApkManager, "htop", ["apk", "del", "htop"], id="apk_remove"),
        pytest.param(
            AptManager, "htop", ["apt-get", "remove", "-y", "htop"], id="apt_remove"
        ),
        pytest.param(
            PacmanManager,
            "htop",
            ["pacman", "-R", "--noconfirm", "htop"],
            id="pacman_remove",
        ),
        pytest.param(
            DnfManager, "htop", ["dnf", "remove", "-y", "htop"], id="dnf_remove"
        ),
    ],
)
def test_get_remove_command(
    manager_class, package, expected_remove_command, mock_path_exists
):
    """Test that each package manager generates correct remove commands."""
    mock_path_exists.return_value = True
    mgr = manager_class()
    assert mgr.get_remove_command(package) == expected_remove_command


@pytest.mark.parametrize(
    "manager_class,expected_upgrade_command",
    [
        pytest.param(ApkManager, ["apk", "upgrade"], id="apk_upgrade"),
        pytest.param(AptManager, ["apt-get", "upgrade", "-y"], id="apt_upgrade"),
        pytest.param(
            PacmanManager, ["pacman", "-Syu", "--noconfirm"], id="pacman_upgrade"
        ),
        pytest.param(DnfManager, ["dnf", "upgrade", "-y"], id="dnf_upgrade"),
    ],
)
def test_get_upgrade_command(manager_class, expected_upgrade_command, mock_path_exists):
    """Test that each package manager generates correct upgrade commands."""
    mock_path_exists.return_value = True
    mgr = manager_class()
    assert mgr.get_upgrade_command() == expected_upgrade_command


@pytest.mark.parametrize(
    "manager_class,expected_id",
    [
        pytest.param(ApkManager, "apk", id="apk_id"),
        pytest.param(AptManager, "apt", id="apt_id"),
        pytest.param(PacmanManager, "pacman", id="pacman_id"),
        pytest.param(DnfManager, "dnf", id="dnf_id"),
    ],
)
def test_manager_id_attribute(manager_class, expected_id):
    """Test that each manager has the correct id attribute."""
    mgr = manager_class()
    assert mgr.id == expected_id


@pytest.mark.parametrize(
    "manager_class",
    [
        pytest.param(ApkManager, id="apk"),
        pytest.param(AptManager, id="apt"),
        pytest.param(PacmanManager, id="pacman"),
        pytest.param(DnfManager, id="dnf"),
    ],
)
def test_manager_is_available_false_when_missing(mock_path_exists, manager_class):
    """Test that managers return False when not available."""
    mock_path_exists.return_value = False
    mgr = manager_class()
    assert mgr.is_available() is False


@pytest.mark.parametrize(
    "manager_class",
    [
        pytest.param(ApkManager, id="apk"),
        pytest.param(AptManager, id="apt"),
        pytest.param(PacmanManager, id="pacman"),
        pytest.param(DnfManager, id="dnf"),
    ],
)
def test_manager_is_available_true_when_available(mock_path_exists, manager_class):
    """Test that managers return True when available."""
    mock_path_exists.return_value = True
    mgr = manager_class()
    assert mgr.is_available() is True
