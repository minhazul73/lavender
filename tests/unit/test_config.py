import stat
from pathlib import Path
from unittest.mock import patch

from server.core.config import _get_or_create_secret_key


def test_secret_key_from_lavender_secret_key_env(monkeypatch):
    monkeypatch.setenv("LAVENDER_SECRET_KEY", "custom-env-secret-key-1234")
    key = _get_or_create_secret_key()
    assert key == "custom-env-secret-key-1234"


def test_secret_key_from_dashboard_secret_key_env(monkeypatch):
    monkeypatch.delenv("LAVENDER_SECRET_KEY", raising=False)
    monkeypatch.setenv("DASHBOARD_SECRET_KEY", "legacy-dashboard-secret-5678")
    key = _get_or_create_secret_key()
    assert key == "legacy-dashboard-secret-5678"


def test_secret_key_auto_generated_and_persisted(tmp_path, monkeypatch):
    monkeypatch.delenv("LAVENDER_SECRET_KEY", raising=False)
    monkeypatch.delenv("DASHBOARD_SECRET_KEY", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    key_file = tmp_path / "lavender" / "secret.key"
    assert not key_file.exists()

    key1 = _get_or_create_secret_key()
    assert len(key1) == 64
    assert key_file.is_file()
    assert key_file.read_text().strip() == key1

    # Check file permissions (0600: read/write for owner only)
    file_mode = stat.S_IMODE(key_file.stat().st_mode)
    assert file_mode == 0o600

    # Subsequent call reuses the existing persisted key
    key2 = _get_or_create_secret_key()
    assert key2 == key1


def test_secret_key_fallback_on_oserror(tmp_path, monkeypatch):
    monkeypatch.delenv("LAVENDER_SECRET_KEY", raising=False)
    monkeypatch.delenv("DASHBOARD_SECRET_KEY", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    with patch.object(Path, "mkdir", side_effect=OSError("Read-only file system")):
        key = _get_or_create_secret_key()
        assert len(key) == 64


def test_host_config_precedence(monkeypatch):
    import importlib

    import server.core.config as config

    # Default host is localhost 127.0.0.1
    monkeypatch.delenv("LAVENDER_HOST", raising=False)
    monkeypatch.delenv("HOST", raising=False)
    importlib.reload(config)
    assert config.HOST == "127.0.0.1"

    # HOST fallback
    monkeypatch.setenv("HOST", "0.0.0.0")
    importlib.reload(config)
    assert config.HOST == "0.0.0.0"

    # LAVENDER_HOST takes precedence
    monkeypatch.setenv("LAVENDER_HOST", "192.168.1.100")
    importlib.reload(config)
    assert config.HOST == "192.168.1.100"

    # Reset
    monkeypatch.delenv("LAVENDER_HOST", raising=False)
    monkeypatch.delenv("HOST", raising=False)
    importlib.reload(config)
    assert config.HOST == "127.0.0.1"

