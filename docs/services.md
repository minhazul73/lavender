# Services & Backend Subsystems

Lavender's backend service layer (`dashboard/services/`) encapsulates system operations and hardware interaction logic.

## Module Breakdown

### 1. `device_info.py`
Dynamically discovers device hardware model and OS metadata without hardcoding specific phone or board models.
- **Device Model Priority:**
  1. Linux Device Tree (`/sys/firmware/devicetree/base/model` or `/proc/device-tree/model`)
  2. postmarketOS / Alpine deviceinfo (`/etc/deviceinfo`)
  3. DMI / SMBIOS (`/sys/class/dmi/id/product_name`)
  4. `hostnamectl` (Chassis / Model)
  5. `/etc/machine-info` (`PRETTY_HOSTNAME`)
  6. `socket.gethostname()`
- **OS Information:** Parses `/etc/os-release` and `/usr/lib/os-release`.
- Results are cached using `@lru_cache(maxsize=1)` as hardware and OS names do not change at runtime.

### 2. `live.py`
Provides real-time metric collection for SSE streaming and sparkline visualization.
- **Data Structures:**
  - `RingBuffer`: Fixed-size circular buffer using `collections.deque(maxlen=size)`. Provides lock-free reads for real-time charts.
  - `CollectorStats`: Tracks per-collector health metrics: `sample_count` (successful collections), `errors_in_row` (consecutive failures), `last_error` (most recent failure message). Exposed via `collector.stats()` for monitoring.
  - `MetricCollector`: Async background collector base class with automatic error recovery, configurable polling intervals, and memory-efficient `__slots__`. Each collector runs as an independent asyncio task.
- **Collectors:**
  - `CPUFreqCollector`: Parses `/proc/stat` for per-core CPU usage calculation and sysfs for scaling frequencies. Reads `cpu_capacity` from `/sys/devices/system/cpu/cpu*/cpu_capacity` for ARM big.LITTLE scheduler capacity information. Cores are sorted numerically to ensure stable ordering across polling intervals. Gracefully handles systems without dynamic frequency scaling (no cpufreq sysfs exposed).
  - `RAMCollector`: Single-file reader for `/proc/meminfo` at 3-second intervals.
  - `ThermalCollector`: Reads from three sources in priority order to avoid duplicates: (1) `hwmon` sysfs (`/sys/class/hwmon/`), (2) platform device thermal (`/sys/bus/platform/devices/`), (3) legacy thermal sysfs (`/sys/class/thermal/`). Maps type names to friendly labels (e.g. `cpu0_thermal` → `CPU0 (Gold)`), flags zones above 70 °C as warnings and 90 °C as critical.
  - `BatteryCollector`: Combines sysfs `/sys/class/power_supply/` and UPower data (`upower -e` / `upower -i`). UPower fields supplement sysfs-only results and take priority for `time_to_empty`, `time_to_full`, and `capacity`. Returns a flat dict (not a dataclass) for JSON serialization in SSE.
  - `NetworkRateCollector`: Reads interface counters from `/proc/net/dev` and computes RX/TX throughput rate deltas. Selects the primary interface using a multi-factor ranking: interface category priority (WiFi > Ethernet > USB > Cellular > Other physical > VPN/overlay), operstate from sysfs, default route detection via `/proc/net/route`, and traffic volume. Virtual interfaces like Tailscale and WireGuard are deprioritized so that physical connections are always preferred on the dashboard.

### 3. `packages.py`
Distro-agnostic package manager abstraction with adapters for:
- `ApkManager`: Alpine Linux / postmarketOS (`apk`)
- `AptManager`: Debian / Ubuntu / Linux Mint / Raspberry Pi OS (`apt` / `dpkg-query`)
- `PacmanManager`: Arch Linux / Manjaro (`pacman`)
- `DnfManager`: Fedora / RHEL (`dnf` / `rpm`)
- Includes an in-memory 60-second cache (`_PACKAGES_CACHE`) for installed package listings to reduce host CPU and disk I/O load. Cache is invalidated via `invalidate_packages_cache()` after install/remove/upgrade operations.
- Convenience wrapper functions: `get_installed_packages()`, `get_installed_count()`, `upgrade_packages()`, `install_package()`, `remove_package()`.

### 4. `systemd.py`
Interfaces with `systemctl` and `journalctl`:
- Supports both system services (`systemctl`) and user services (`systemctl --user`).
- Automatically preserves or injects `XDG_RUNTIME_DIR` (`/run/user/<uid>`) and `DBUS_SESSION_BUS_ADDRESS` for non-interactive user service management.
- Parses structured journal logs (`journalctl -o json`). Converts `__REALTIME_TIMESTAMP` (or `_SOURCE_REALTIME_TIMESTAMP`) microsecond-epoch values to ISO 8601 format, with heuristic detection for seconds vs milliseconds vs microseconds. Falls back to `SYSLOG_TIMESTAMP` when no numeric timestamp is available.
- Service status parsing extracts: unit file state (enabled/disabled/static/masked), active state, sub-state, CPU time, and documentation links.
- Logs are truncated to 200 characters per entry and include severity levels derived from syslog priority (error ≤ 2, warning ≤ 4, info ≤ 6).

### 5. `storage.py`
Disk usage and filesystem inspection:
- Runs `df -h` and filters out virtual/pseudo filesystems (`tmpfs`, `devpts`, `proc`, `sysfs`, `cgroup`).
- Filters system mount points (`/boot`, `/run/docker/`, `/var/lib/docker/`).
- Identifies user-facing external storage (`/mnt`, `/media`, `/sdcard`).
- Reports total, used, available, and percentage for each mount point.

### 6. `processes.py`
Process list monitor supporting dual formats:
- Standard `procps` (`ps aux`, 11 columns).
- BusyBox `ps aux` (4 columns) with fallback `/proc/<pid>/stat` inspection for RSS/VSZ and memory percentage calculation.
- Supports sorting by CPU, memory, PID, user, or name. Process termination requires admin privileges (`kill -9`).

### 7. `network.py`
Comprehensive network diagnostics and Wi-Fi interface management:
- Dual IP address detection via `ip -j addr show` and fallback `/sys/class/net` parsing.
- Interface categorization: loopback, wireless, ethernet, bridge, virtual, cellular.
- Wi-Fi status integration across `nmcli`, `iwconfig`, `iw`, `wpa_cli`, and `/proc/net/wireless`.
- Default route and gateway discovery via `ip route show` (JSON and text fallback).
- DNS provider auto-identification: Cloudflare, Google, Quad9, AdGuard, OpenDNS, Local Router/Gateway, ISP/Custom.
- Latency tools: Ping latency tests and domain resolution diagnostics.

### 8. `battery.py`
Battery, thermal, and CPU frequency management:
- **Battery:** Reads sysfs `/sys/class/power_supply/` and UPower data (`upower -e` / `upower -i`) for capacity, voltage, charge cycles, and state.
- **Thermal Zones:** Scans `/sys/class/thermal/thermal_zone*`, mapping type names to friendly labels (e.g. `cpu0_thermal` → `CPU0 (Gold)`) and flagging zones above 70 °C as warnings.
- **CPU Frequencies:** Iterates `/sys/devices/system/cpu/cpu*/cpufreq/` for current frequency and scaling governor. Filters out non-CPU entries (e.g. `cpufreq`) by requiring `entry[3:].isdigit()` so only `cpu0`, `cpu1`, etc. are processed.
- **CPU Scaling:** Reads `cpu0/cpufreq` for available governors and min/max frequency ranges.
- **Uptime:** Wraps `uptime` command output for human-readable system up time.

### 9. `users.py`
User and group account management:
- Enriched `/etc/passwd` parsing separating human accounts (UID ≥ 1000) from system daemon accounts.
- Categorizes Linux groups into `Privileged`, `Hardware`, `Services`, and `System` with human-readable descriptions.
- Parses public SSH keys from `~/.ssh/authorized_keys`.
- Audits system security posture (`sudo`, `doas`, `visudo`, `sshd_config`).
- Enumerates active terminal and SSH sessions and recent login history.
- Supports password changes and group membership updates.

### 10. `power.py`
System power control operations:
- Wrappers for `reboot`, `poweroff`, and `suspend` via `systemctl`.
- Scheduled shutdown/reboot support with configurable delay and message.
- Cancellation of pending scheduled power actions.

## Auth & Security Bridge (`dashboard/auth/`)

### `bridge.py`
Authentication and command execution bridge:
- Multi-stage Linux credential verification: direct shadow verification → PAM services → sudo validation → doas validation.
- **Async command execution:** `run_command_async()` and `run_sudo_async()` provide non-blocking subprocess execution with timeout handling and process cleanup on expiry.
- **User service execution:** `run_user_service_async()` injects `XDG_RUNTIME_DIR` and `DBUS_SESSION_BUS_ADDRESS` for `systemctl --user` commands, preventing "Failed to connect to bus" errors in non-interactive sessions.

### `session.py`
In-memory session store with sliding idle timeout and background purge task.

### `deps.py`
FastAPI dependency injectors: `get_current_session`, `require_session`, `require_admin`.
