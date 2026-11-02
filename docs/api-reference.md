# API Reference

Lavender exposes RESTful JSON endpoints and a Server-Sent Events (SSE) telemetry stream. Protected endpoints require an active session cookie (`lavender_session`), and privileged operations require administrative elevation.

---

## 1. Authentication (`/auth/*`)

| Method | Endpoint | Access | Description | Payload / Query |
|:---|:---|:---|:---|:---|
| `POST` | `/auth/login` | Public | Authenticate credentials; sets signed session cookie | Form or JSON: `{"username": "...", "password": "..."}` |
| `GET, POST` | `/auth/logout` | Session | Clear session, drop sudo ticket, and delete cookie | None |
| `GET` | `/auth/me` | Session | Retrieve active user profile, UID/GID, groups, and admin elevation status | None |
| `POST` | `/auth/elevate` | Session | Elevate privileges via password check and sudo ticket | JSON: `{"password": "..."}` |
| `POST` | `/auth/drop-admin` | Session | Revoke elevated privileges and purge sudo ticket (`sudo -k`) | None |

---

## 2. Storage & Web File Browser (`/api/storage/*`)

| Method | Endpoint | Access | Description | Payload / Query |
|:---|:---|:---|:---|:---|
| `GET` | `/api/storage` | Session | Get disk partitions, mount usage, and top directory breakdown | None |
| `POST` | `/api/storage/unmount` | Admin | Unmount filesystem or external drive | JSON: `{"mount_point": "..."}` |
| `GET` | `/api/storage/files` | Session | List directory contents with metadata (size, permissions, timestamps) | Query: `?path=/path/to/dir` |
| `GET` | `/api/storage/bookmarks` | Session | Retrieve quick-access drive bookmarks and system shortcuts | None |
| `GET` | `/api/storage/file/view` | Session | Read/preview text file content with line limit | Query: `?path=/path/to/file` |
| `GET` | `/api/storage/file/raw` | Session | Stream or download raw file content (images, media, documents) | Query: `?path=/path/to/file` |
| `POST` | `/api/storage/file/save` | Admin* | Save updated text content to file | JSON: `{"path": "...", "content": "..."}` |
| `POST` | `/api/storage/mkdir` | Session | Create a new folder | JSON: `{"path": "...", "name": "..."}` |
| `POST` | `/api/storage/file/create`| Session | Create an empty new file | JSON: `{"path": "...", "name": "..."}` |
| `POST` | `/api/storage/rename` | Session | Rename a file or folder | JSON: `{"old_path": "...", "new_name": "..."}` |
| `POST` | `/api/storage/delete` | Session | Delete single or multiple files/folders | JSON: `{"paths": ["/path/1", "/path/2"]}` |
| `POST` | `/api/storage/upload` | Session | Upload files to destination directory | Multipart form: `destination`, `files` |

*\*Admin required for writing outside the user's home directory or modifying system files.*

---

## 3. System & Services (`/api/system/*`)

| Method | Endpoint | Access | Description | Payload / Query |
|:---|:---|:---|:---|:---|
| `GET` | `/api/system/services` | Session | List systemd units | Query: `?scope=user\|system\|all` |
| `GET` | `/api/system/services/{unit}` | Session | Get detailed unit status and properties | Query: `?user=true\|false` |
| `GET` | `/api/system/services/{unit}/logs` | Session | Fetch recent journalctl logs for service unit | Query: `?lines=50&user=bool` |
| `POST` | `/api/system/services/{unit}/{action}` | Admin | Execute action (`start`, `stop`, `restart`, `enable`, `disable`) | Query: `?user=bool` |
| `GET` | `/api/system/processes` | Session | List running processes and system load stats | Query: `?sort_by=cpu\|mem\|pid\|user\|name&limit=20` |
| `POST` | `/api/system/processes/kill` | Admin | Terminate process by PID (`kill -9`) | Query: `?pid={n}` |
| `GET` | `/api/system/memory` | Session | Get human-readable and raw memory statistics | None |
| `GET` | `/api/system/logs` | Session | Fetch recent system journal entries | Query: `?lines=50` |

---

## 4. Network & Diagnostics (`/api/network/*`)

| Method | Endpoint | Access | Description | Payload / Query |
|:---|:---|:---|:---|:---|
| `GET` | `/api/network` | Session | Get network interfaces, carrier states, IP addresses, DNS, and gateway | None |
| `GET` | `/api/network/ping` | Session | Execute ping latency test to target | Query: `?target=1.1.1.1&count=4` |
| `GET` | `/api/network/dns-query` | Session | Perform DNS lookup latency diagnostic | Query: `?domain=example.com` |
| `POST` | `/api/network/wifi-scan` | Session | Trigger Wi-Fi scan for nearby wireless networks | None |

---

## 5. Package Management (`/api/packages/*`)

| Method | Endpoint | Access | Description | Payload / Query |
|:---|:---|:---|:---|:---|
| `GET` | `/api/packages` | Session | Installed count, active package manager backend, and upgradable list | None |
| `GET` | `/api/packages/search` | Session | Search upstream distribution repositories | Query: `?query={name}` |
| `GET` | `/api/packages/info` | Session | Retrieve detailed package metadata | Query: `?package={name}` |
| `POST` | `/api/packages/upgrade` | Admin | Upgrade all packages or a single specified package | Optional JSON: `{"package": "..."}` |
| `POST` | `/api/packages/install` | Admin | Install package | JSON: `{"package": "..."}` |
| `POST` | `/api/packages/remove` | Admin | Remove package | JSON: `{"package": "..."}` |

---

## 6. Power Management & Governors (`/api/power/*`)

| Method | Endpoint | Access | Description | Payload / Query |
|:---|:---|:---|:---|:---|
| `GET` | `/api/power/state` | Session | Battery, thermal, current and available CPU governors, scheduled actions | None |
| `POST` | `/api/power/governor` | Admin | Set CPU frequency scaling governor across all cores | JSON: `{"governor": "powersave\|performance\|schedutil"}` |
| `POST` | `/api/power/schedule` | Admin | Schedule a shutdown or reboot with broadcast message | JSON: `{"action": "reboot\|poweroff", "minutes": 15, "message": "..."}` |
| `POST` | `/api/power/cancel-scheduled` | Admin | Cancel pending scheduled shutdown/reboot | None |
| `POST` | `/api/power/reboot` | Admin | Reboot host immediately | None |
| `POST` | `/api/power/poweroff` | Admin | Power off host immediately | None |
| `POST` | `/api/power/suspend` | Admin | Suspend host immediately | None |

---

## 7. Users, Sessions & SSH Keys (`/api/users/*`)

| Method | Endpoint | Access | Description | Payload / Query |
|:---|:---|:---|:---|:---|
| `GET` | `/api/users` | Session | Human vs system accounts, active sessions, and security posture | None |
| `POST` | `/api/users/session/terminate`| Admin | Terminate active terminal/SSH session (`who -u`) | JSON: `{"tty": "...", "pid": 1234}` |
| `GET` | `/api/users/{user}/ssh-keys` | Session | List public keys in `authorized_keys` | None |
| `POST` | `/api/users/{user}/ssh-keys` | Admin | Add public SSH key to user's authorized keys | JSON: `{"key": "ssh-ed25519 ..."}` |
| `DELETE`| `/api/users/{user}/ssh-keys/{idx}` | Admin | Delete public SSH key by 0-indexed line position | None |
| `POST` | `/api/users/{user}/groups` | Admin | Update secondary group memberships | JSON: `{"groups": ["wheel", "docker"]}` |
| `POST` | `/api/users/{user}/password`| Self/Admin | Change user password | JSON: `{"current_password": "...", "new_password": "..."}` |

---

## 8. Device Info (`/api/device/*`)

| Method | Endpoint | Access | Description |
|:---|:---|:---|:---|
| `GET` | `/api/device/info` | Public | Retrieve hardware model, OS release, kernel, architecture, and hostname |
| `GET` | `/api/device/battery` | Public | Battery status, thermal zones, and current CPU frequencies |

---

## 9. Live Streaming Telemetry (SSE)

| Method | Endpoint | Access | Description |
|:---|:---|:---|:---|
| `GET` | `/api/device/live` (or `/api/live`) | Public | Stream continuous Server-Sent Events with metrics (`?metrics=cpu,ram,thermal,battery,network`) |

---

## 10. Backward Compatibility Aliases

To prevent breaking existing scripts, curl commands, and automation webhooks, all legacy endpoint aliases remain active:

- `/api/device/network/*` ➔ `/api/network/*`
- `/api/device/packages/*` ➔ `/api/packages/*`
- `/api/device/power/*` ➔ `/api/power/*`
- `/api/device/users/*` ➔ `/api/users/*`
- `/api/system/storage` ➔ `/api/storage`
- `/api/services/*` ➔ `/api/system/services/*`
- `/api/processes/*` ➔ `/api/system/processes/*`
