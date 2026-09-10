import os
import secrets

PORT = 8080
HOST = "0.0.0.0"
DEBUG = False

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
SESSION_COOKIE_NAME = "rn7_session"
SESSION_MAX_IDLE_MINUTES = 60
ADMIN_ELEVATION_TIMEOUT_MINUTES = 15
SESSION_SECRET_KEY = os.environ.get("DASHBOARD_SECRET_KEY", "rn7-dashboard-secret-key-default-2026")

# SSH Loopback Bridge Settings
SSH_LOOPBACK_HOST = os.environ.get("SSH_HOST", "127.0.0.1")
SSH_LOOPBACK_PORT = int(os.environ.get("SSH_PORT", "22"))
SSH_LOGIN_TIMEOUT = 10  # seconds

# Rate Limiting
LOGIN_RATE_LIMIT = "10/minute"
