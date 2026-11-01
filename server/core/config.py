import logging
import os
from pathlib import Path
import secrets

logger = logging.getLogger(__name__)

PORT = int(os.environ.get("LAVENDER_PORT", os.environ.get("PORT", "8080")))
HOST = os.environ.get("LAVENDER_HOST", os.environ.get("HOST", "0.0.0.0"))
DEBUG = os.environ.get("LAVENDER_DEBUG", "false").lower() in ("1", "true", "yes")

# Application Version (SemVer: < 1.0 indicates development / pre-release status)
APP_VERSION = "0.4.0"

# Sudo commands that need elevation (documented limitation)
SUDO_COMMANDS = {
    "systemctl_system": ["sudo", "systemctl"],
    "apk_upgrade": ["sudo", "apk", "upgrade"],
    "apk_add": ["sudo", "apk", "add"],
    "apk_del": ["sudo", "apk", "del"],
    "reboot": ["sudo", "systemctl", "reboot"],
    "poweroff": ["sudo", "systemctl", "poweroff"],
    "suspend": ["sudo", "systemctl", "suspend"],
    "kill": ["sudo", "kill", "-9"],  # Some processes need root to kill
}

# Thermal threshold (millidegrees C) — warn above this
THERMAL_WARN_THRESHOLD = 70000  # 70°C

# Memory pressure threshold (fraction of RAM used)
MEMORY_PRESSURE_THRESHOLD = 0.85

# Number of lines for logs
LOG_LINES = 50

# Top N processes
TOP_PROCESSES = 20

# Top N directories for du
TOP_DIRS = 10

# ===== SSE Live Monitoring =====
# Default SSE poll intervals (ms) — each metric has its own
SSE_CPU_INTERVAL_MS = 1000      # CPU freq: every 1s
SSE_RAM_INTERVAL_MS = 3000      # RAM: every 3s
SSE_THERMAL_INTERVAL_MS = 5000  # Thermal: every 5s
SSE_BATTERY_INTERVAL_MS = 3000  # Battery: every 3s
SSE_NETWORK_INTERVAL_MS = 2000  # Network rate: every 2s

# Rolling buffer sizes (number of datapoints kept per metric)
SSE_CPU_BUFFER = 30
SSE_RAM_BUFFER = 20
SSE_THERMAL_BUFFER = 20
SSE_BATTERY_BUFFER = 30
SSE_NETWORK_BUFFER = 30

# ===== Auth & Session Settings =====
SESSION_COOKIE_NAME = "lavender_session"
SESSION_MAX_IDLE_MINUTES = 60
ADMIN_ELEVATION_TIMEOUT_MINUTES = 15
def _get_or_create_secret_key() -> str:
    """Autonomously manage secret key lifecycle with zero user configuration.

    1. Check optional env override (for clustered/container setups).
    2. Read existing key from ~/.config/lavender/secret.key (or $XDG_CONFIG_HOME).
    3. Autonomously generate a 256-bit secure key and persist with 0600 permissions.
    4. Fall back to ephemeral in-memory key if filesystem is read-only.
    """
    env_key = os.environ.get("LAVENDER_SECRET_KEY") or os.environ.get("DASHBOARD_SECRET_KEY")
    if env_key:
        return env_key

    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    key_dir = Path(xdg_config) / "lavender" if xdg_config else Path.home() / ".config" / "lavender"
    key_file = key_dir / "secret.key"

    try:
        if key_file.is_file():
            stored = key_file.read_text().strip()
            if stored:
                return stored

        key_dir.mkdir(parents=True, exist_ok=True)
        new_key = secrets.token_hex(32)
        key_file.write_text(new_key)
        try:
            key_file.chmod(0o600)
        except OSError:
            pass
        return new_key
    except OSError as err:
        logger.warning("Could not persist secret key to %s (%s). Falling back to ephemeral key.", key_file, err)
        return secrets.token_hex(32)


SESSION_SECRET_KEY = _get_or_create_secret_key()
PAM_SERVICE = os.environ.get("PAM_SERVICE", "login")

# Auth requirement for homepage / overview stats
# When False (default): homepage is public for viewing device telemetry stats without execution privileges.
# When True: homepage is locked behind auth and requires login.
REQUIRE_AUTH_FOR_HOMEPAGE = os.environ.get(
    "LAVENDER_REQUIRE_AUTH_FOR_HOMEPAGE",
    os.environ.get("REQUIRE_AUTH_FOR_HOMEPAGE", "false")
).lower() in ("1", "true", "yes")

# Rate Limiting
LOGIN_RATE_LIMIT = "10/minute"

