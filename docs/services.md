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
  - `MetricCollector`: Async background collector base class with automatic error recovery and configurable polling intervals.
- **Collectors:**
  - `CPUFreqCollector`: Parses `/proc/stat` for per-core CPU usage calculation and sysfs for scaling frequencies.
  - `RAMCollector`: Single-file reader for `/proc/meminfo`.
  - `ThermalCollector`: Sysfs reader for `/sys/class/thermal/` with friendly label mapping.
  - `BatteryCollector`: Combines sysfs `/sys/class/power_supply/` and UPower data.
  - `NetworkCollector`: Computes RX/TX throughput rate deltas from `/sys/class/net/*/statistics`.

### 3. `packages.py`
Distro-agnostic package manager abstraction with adapters for:
- `ApkManager`: Alpine Linux / postmarketOS (`apk`)
- `AptManager`: Debian / Ubuntu / Linux Mint / Raspberry Pi OS (`apt` / `dpkg-query`)
- `PacmanManager`: Arch Linux / Manjaro (`pacman`)
- `DnfManager`: Fedora / RHEL (`dnf` / `rpm`)
- Includes an in-memory 60-second cache (`_PACKAGES_CACHE`) for installed package listings to reduce host CPU and disk I/O load.

### 4. `systemd.py`
Interfaces with `systemctl` and `journalctl`:
- Supports both system services (`systemctl`) and user services (`systemctl --user`).
- Automatically preserves or injects `XDG_RUNTIME_DIR` (`/run/user/<uid>`) and `DBUS_SESSION_BUS_ADDRESS` for non-interactive user service management.
- Parses structured journal logs (`journalctl -o json`).

### 5. `storage.py`
Disk usage and filesystem inspection:
- Runs `df -h` and filters out virtual/pseudo filesystems (`tmpfs`, `devpts`, `proc`, `sysfs`, `cgroup`).
- Filters system mount points (`/boot`, `/run/docker/`, `/var/lib/docker/`).
- Identifies user-facing external storage (`/mnt`, `/media`, `/sdcard`).

### 6. `processes.py`
Process list monitor supporting dual formats:
- Standard `procps` (`ps aux`, 11 columns).
- BusyBox `ps aux` (4 columns) with fallback `/proc/<pid>/stat` inspection for RSS/VSZ and memory percentage calculation.

### 7. `network.py`
Comprehensive network diagnostics and Wi-Fi interface management:
- Dual IP address detection via `ip -j addr show` and fallback `/sys/class/net` parsing.
- Wi-Fi status integration across `nmcli`, `iwconfig`, `iw`, `wpa_cli`, and `/proc/net/wireless`.
- Latency tools: Ping latency tests and domain resolution diagnostics.

### 8. `users.py`
User and group account management:
- Enriched `/etc/passwd` parsing separating human accounts (UID ≥ 1000) from system daemon accounts.
- Categorizes Linux groups into `Privileged`, `Hardware`, `Services`, and `System` with human-readable descriptions.
- Parses public SSH keys from `~/.ssh/authorized_keys`.
- Audits system security posture (`sudo`, `doas`, `visudo`, `sshd_config`).
