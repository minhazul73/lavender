PORT = 8080
HOST = "0.0.0.0"
DEBUG = False

# Hermes paths
HERMES_BIN = "/home/rahat/.local/bin/hermes"
HERMES_HOME = "/home/rahat/.hermes"
HERMES_CRON_DIR = f"{HERMES_HOME}/cron"
HERMES_STATE_DB = f"{HERMES_HOME}/state.db"

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
