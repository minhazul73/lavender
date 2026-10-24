# Features Deep Dive

Lavender provides a comprehensive suite of Linux system management tools wrapped in a responsive, modern web interface.

---

## 1. Live Monitoring via Server-Sent Events (SSE)

Real-time telemetry streams from the host to the browser using lightweight Server-Sent Events (SSE). Unlike WebSockets, SSE operates over standard HTTP, making it firewall-friendly and reconnect-resilient.

- **CPU Metrics:**
  - Real-time per-core and aggregate CPU usage calculated from `/proc/stat`.
  - Dynamic CPU scaling frequencies read from `/sys/devices/system/cpu/*/cpufreq/scaling_cur_freq`.
  - 1-minute, 5-minute, and 15-minute load averages.
  - Ring-buffered sparklines showing rolling usage history.
- **Memory & Swap:**
  - Memory consumption statistics (`MemTotal`, `MemFree`, `MemAvailable`, `Buffers`, `Cached`, `SwapTotal`, `SwapFree`) parsed from `/proc/meminfo`.
  - Visual gauge indicators with color-coded warnings when memory pressure threshold is exceeded.
- **Thermal Management:**
  - Multi-zone temperature monitoring across `hwmon`, platform drivers, and thermal sysfs (`/sys/class/thermal/thermal_zone*`).
  - Friendly hardware label resolution (e.g. mapping `thermal_zone0` to `CPU`, `GPU`, or `Battery`).
  - Warning (70°C) and critical (85°C) threshold badges.
- **Battery & Power Draw:**
  - Live capacity percentage, charging/discharging/full status, and power supply health via `/sys/class/power_supply` (with UPower fallback).
  - Voltage progress meter, energy consumption rate in Watts, battery temperature, and estimated time to full/empty.
- **Network Rate:**
  - Real-time RX/TX throughput rate calculations (in KB/s or MB/s).
  - Automatic deprioritization of virtual/VPN interfaces (e.g., Tailscale `tailscale0` or wireguard) so primary network throughput is accurately reflected.
- **Top Resource Consumers:**
  - Auto-refreshing top resource consumer table (updated every 5 seconds).
  - Sticky table headers with PID, user, CPU %, memory %, and command string.

---

## 2. Storage & Web File Browser

Lavender pairs disk capacity monitoring with an embedded Web File Manager:

- **Storage & Partitions:**
  - Visual filesystem capacity bars with total, used, available, and percentage breakdown.
  - Automatic filtering of pseudo/virtual filesystems (`tmpfs`, `devpts`, `sysfs`).
  - Detection and highlighting of removable media and external drives (`/mnt`, `/media`, `/sdcard`).
  - One-click partition unmounting (`/api/storage/unmount`) with administrative protection.
- **Interactive File Explorer:**
  - Directory tree browsing with dynamic breadcrumb navigation.
  - Quick-access bookmarks and drive shortcuts (Home, Root, Media, Mounts).
  - Search and filter files by name within the current directory.
- **In-Browser File Viewing & Editing:**
  - Integrated text viewer and editor for configuration files, scripts, logs, and markdown.
  - Syntax-friendly monospace display with line numbers.
  - In-place saving with administrative privileges for protected system files.
- **Media Preview & Raw Streaming:**
  - In-browser preview for images, audio, video, and documents.
  - Direct download links for any file.
- **File Management Operations:**
  - Create new files and folders (`mkdir`).
  - Rename files and directories.
  - Single or bulk deletion with confirmation safety modals.
  - Multi-file drag-and-drop or file-picker upload to the current directory.
  - Strict path traversal defenses preventing directory escape attacks.

---

## 3. Distro-Agnostic Package Management

Lavender includes a multi-backend adapter architecture that automatically detects and interfaces with the host distribution's native package manager:

| Distribution | Package Manager | Backend Adapter |
|:---|:---|:---|
| **Alpine Linux / postmarketOS** | `apk` | `ApkBackend` |
| **Debian / Ubuntu / Linux Mint** | `apt` / `dpkg-query` | `AptBackend` |
| **Arch Linux / Manjaro** | `pacman` | `PacmanBackend` |
| **Fedora / RHEL / CentOS** | `dnf` / `rpm` | `DnfBackend` |

- **Features:**
  - 60-second in-memory TTL caching for fast package queries.
  - List installed packages and filter upgradable packages.
  - Upstream repository search for package availability.
  - Inspect detailed package metadata, versions, licenses, and descriptions.
  - Install or remove packages with admin confirmation.
  - Run single-package upgrades or full system updates.

---

## 4. Systemd Service Management

Comprehensive control over system and user services via `systemctl`:

- **Scope & State Filtering:** Filter units by scope (`user`, `system`, `all`) and state (`active`, `inactive`, `failed`).
- **Search & Pagination:** Fast client-side search across service names and descriptions with configurable page limits.
- **Lifecycle Actions:** Start, stop, restart, enable, and disable services.
- **Interactive Journalctl Terminal:**
  - Embedded dark terminal log viewer for any selected service unit.
  - Fetches recent journal entries with timestamp parsing.
  - One-click copy for `journalctl -u <unit>` debugging commands.

---

## 5. Process Explorer & Resource Monitor

Interactive process table supporting both standard `procps` and embedded `busybox ps`:

- **Sorting:** Multi-column sorting by CPU %, Memory %, PID, User, or Process Name.
- **Expandable Command Details:** Click any row to expand the full command-line invocation, working directory, and parameters with instant copy support.
- **Safe Termination:** Terminate misbehaving or hung processes (`kill -9`) with administrative confirmation dialogs.

---

## 6. Network & Diagnostic Tools

- **Interface Inspection:** Real-time interface states, carrier detection, IPv4/IPv6 addresses, MAC addresses, MTU, and RX/TX counters.
- **Wi-Fi Scanner:** Scan nearby wireless access points with SSID, BSSID, signal strength bars, channel, frequency, bitrate, and security protocol (WPA2/WPA3). Supports `nmcli`, `iw`, `iwconfig`, and `wpa_cli`.
- **DNS Server Detection:** Lists active nameservers with auto-detected provider labels (Cloudflare, Google, Quad9, AdGuard, OpenDNS, Local Gateway).
- **Interactive Diagnostics:**
  - Built-in ping tool with target host, packet count, and latency stats.
  - DNS lookup test measuring resolution latency in milliseconds.
  - Default route and gateway discovery.

---

## 7. Identity & Access Control

- **Human vs. System Accounts:** Separates human interactive users (UID ≥ 1000) from system service daemons.
- **Home Storage Partition:** Displays total, used, free GB, and usage percentage for each user's home directory.
- **Active Sessions:** Track active terminal and SSH sessions (`who -u`, TTY, remote IP, login time, idle duration) with one-click remote session termination.
- **SSH Public Keys:** View, add, and delete public keys in `~/.ssh/authorized_keys`.
- **User Passwords:** Self-service password changes for authenticated users and administrative password resets.
- **Categorized Groups:** Inspect and edit group memberships across Privileged (`wheel`, `sudo`, `docker`), Hardware subsystems (`audio`, `video`, `netdev`, `input`, `bluetooth`), Service daemons (`nginx`, `caddy`, `postgres`), and System groups.
- **Security Posture Audit:** Audits elevation engines (`sudo` / `doas`), `visudo -c` syntax validation, OpenSSH daemon status (`sshd`), `PermitRootLogin`, `PasswordAuthentication` settings, and recent login history via `last`.

---

## 8. Power Management & CPU Profiles

- **Lifecycle Actions:** Modal-confirmed `reboot`, `poweroff`, and `suspend` operations protected by administrative elevation.
- **CPU Scaling Governors:** Live governor detection and one-click switching across all CPU cores (`powersave`, `schedutil`, `ondemand`, `performance`).
- **Scheduled Power Actions:**
  - Quick presets (5m, 15m, 30m, 60m) or custom countdown timers.
  - Broadcast wall message support (`shutdown -r +N`, `shutdown -h +N`).
  - Persistent countdown banner with one-click cancellation (`shutdown -c`).

---

## 9. Mobile-First Responsive Design

- **Dynamic Viewport Height (`--dvh`):** Layouts automatically adapt to mobile browser URL bar collapsing and virtual keyboard appearances without breaking scroll containers.
- **Safe Area Insets:** Native support for `env(safe-area-inset-*)` ensuring UI elements do not collide with notches or gesture bars on Linux phones (e.g., Redmi Note 7, PinePhone).
- **Responsive Navigation:** Desktop collapsible sidebar transitions seamlessly into a compact mobile navigation drawer and bottom bar.
