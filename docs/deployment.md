# Production Deployment Guide

Lavender is designed to run with minimal overhead as a background daemon or systemd service on Linux devices ranging from ARM64 single-board computers to x86_64 servers.

---

## 1. System Requirements

- **Operating System:** Any Linux distribution (Alpine, postmarketOS, Debian, Ubuntu, Arch Linux, Fedora, CentOS, etc.)
- **Python:** Python 3.11 or newer
- **PAM Headers:** `linux-pam-dev` (Alpine) or `libpam0g-dev` (Debian/Ubuntu)
- **Privileges:** Standard user with `sudo` or `doas` access for administrative actions

> [!NOTE]
> Node.js, Bun, and npm are **NOT required** on production devices. Releases include pre-compiled frontend assets in `server/dist/`.

---

## 2. Installation Methods

### Option A: Using `uv` (Recommended)

```bash
git clone https://github.com/minhazul73/lavender.git
cd lavender
uv sync
```

### Option B: Using Standard Python `venv`

```bash
git clone https://github.com/minhazul73/lavender.git
cd lavender
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 3. Running as a Systemd Service

Lavender includes a production-ready systemd unit template in [`systemd/lavender.service`](file:///home/rahat/Documents/vscode/FASTAPI/lavender/systemd/lavender.service).

### Running as a User Service (Recommended)

Running as a systemd user service isolates Lavender to the current user's security context:

```bash
# 1. Create systemd user config directory
mkdir -p ~/.config/systemd/user/

# 2. Copy the unit file
cp systemd/lavender.service ~/.config/systemd/user/

# 3. Edit paths to match your environment
# Ensure WorkingDirectory and ExecStart point to your lavender repository and virtualenv python
nano ~/.config/systemd/user/lavender.service

# 4. Enable and start the service
systemctl --user daemon-reload
systemctl --user enable --now lavender

# 5. Verify service status
systemctl --user status lavender
```

To ensure user services continue running after logout:
```bash
sudo loginctl enable-linger $USER
```

### Running as a System Service

To run as a system daemon managed by root:

```bash
sudo cp systemd/lavender.service /etc/systemd/system/lavender.service
# Edit User, Group, WorkingDirectory, and ExecStart
sudo nano /etc/systemd/system/lavender.service
sudo systemctl daemon-reload
sudo systemctl enable --now lavender
```

---

## 4. Important Systemd Configuration: `NoNewPrivileges=no`

Lavender uses `sudo` and PAM `unix_chkpwd` for authentication and Cockpit-style elevation.

In your service unit file:
```ini
[Service]
# MUST BE SET TO 'no':
NoNewPrivileges=no
```

> [!WARNING]
> If `NoNewPrivileges=yes` is enabled, the Linux kernel prevents setuid execution, causing `sudo` and PAM password checks to fail.

---

## 5. Reverse Proxy Configuration

If you want to expose Lavender through an HTTPS domain, configure a reverse proxy such as Caddy or Nginx.

### Caddy Example

```caddy
lavender.yourdomain.com {
    reverse_proxy 127.0.0.1:8080
}
```

### Nginx Example

```nginx
server {
    listen 80;
    server_name lavender.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Disable buffering for SSE live streaming
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
    }
}
```
