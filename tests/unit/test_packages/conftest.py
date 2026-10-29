"""Shared fixtures for package manager unit tests."""

from unittest.mock import patch

import pytest


@pytest.fixture
def mock_run_command():
    """Mock run_command with default successful return."""
    with patch("dashboard.services.packages.run_command") as mock:
        mock.return_value = (0, "", "")
        yield mock


@pytest.fixture
def mock_run_command_failure():
    """Mock run_command to simulate failure."""
    with patch("dashboard.services.packages.run_command") as mock:
        mock.return_value = (1, "", "command failed")
        yield mock


@pytest.fixture
def mock_path_exists():
    """Mock os.path.exists for availability checks."""
    with patch("dashboard.services.packages.shutil.which") as mock:
        mock.return_value = None
        yield mock


@pytest.fixture
def mock_run_sudo_command():
    """Mock run_sudo_command with default successful return."""
    with patch("dashboard.services.packages.run_sudo_command") as mock:
        mock.return_value = (0, "OK", "")
        yield mock


@pytest.fixture
def apk_installed_packages_output():
    """Sample output from 'apk list -I' command."""
    return (0, "musl-1.2.4-r0\nbusybox-1.36.1-r2\n", "")


@pytest.fixture
def apt_installed_packages_output():
    """Sample output from 'dpkg-query -W' command."""
    return (0, "htop\t3.3.0\tamd64\nvim\t9.0\tamd64\n", "")


@pytest.fixture
def pacman_installed_packages_output():
    """Sample output from 'pacman -Q' command."""
    return (0, "htop 3.3.0-1\nvim 9.0-1\n", "")


@pytest.fixture
def dnf_installed_packages_output():
    """Sample output from 'dnf list installed' command."""
    return (0, "htop\t3.3.0-1\tx86_64\n", "")
