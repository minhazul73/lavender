# Authentication & Security

Lavender provides native Linux authentication and fine-grained, role-based privilege elevation without requiring SSH loopback sockets or external authentication servers.

---

## 1. Authentication Pipeline

When a user signs in at `/auth/login`, credentials undergo multi-stage verification against the local Linux system in [`server/auth/bridge.py`](file:///home/rahat/Documents/vscode/FASTAPI/lavender/server/auth/bridge.py):

1. **Direct `/etc/shadow` Verification:**
   - If Lavender is running as `root` or has read access to `/etc/shadow`, it computes and verifies crypt hashes directly.
2. **Linux PAM (Pluggable Authentication Modules):**
   - Uses `python-pam` against standard Linux PAM services (`PAM_SERVICE`, with fallback to `base-auth`, `login`, `su`, or `system-auth`).
3. **Sudo Credential Check:**
   - Validates user password against `sudo -S -p '' -v` via non-blocking asynchronous subprocesses.
4. **Doas Verification:**
   - If `doas` is present (common on Alpine Linux/BSD), validates against `doas -C /etc/doas.conf true`.

---

## 2. Session Management & Cryptographic Cookies

- **Session Store:** Sessions are held in-memory via `SessionStore` ([`server/auth/session.py`](file:///home/rahat/Documents/vscode/FASTAPI/lavender/server/auth/session.py)).
- **Cookie Serialization:** A signed HTTP-only cookie named `lavender_session` is issued using `itsdangerous.URLSafeTimedSerializer`.
- **Sliding Idle Expiration:** Sessions expire after **60 minutes** of inactivity (`SESSION_MAX_IDLE_MINUTES`). Any authenticated request refreshes the session timestamp.
- **Background Purge:** An asynchronous background task runs every 5 minutes during FastAPI's lifespan to purge inactive sessions.

---

## 3. Cockpit-Style Privilege Elevation

To adhere to the principle of least privilege, standard users sign in with regular user privileges. Sensitive operations (such as installing packages, modifying systemd units, editing system files, or powering off) require administrative elevation:

1. **Eligibility Check:**
   - Only users belonging to administrative groups (`wheel`, `sudo`, `root`) or having UID 0 can elevate.
   - Root accounts (`root` / UID 0) are automatically and permanently elevated.
2. **Elevation Workflow:**
   - The user enters their password in the elevation prompt (`POST /auth/elevate`).
   - The backend validates the password and executes `sudo -v`, refreshing a temporary local sudo timestamp ticket for **15 minutes** (`ADMIN_ELEVATION_TIMEOUT_MINUTES`).
   - The UI top bar updates to indicate elevated status.
3. **Revocation (`/auth/drop-admin`):**
   - Elevated users can revoke privileges at any time with a single click.
   - Revocation marks the session as non-elevated and immediately calls `sudo -k` to drop the host timestamp ticket.

---

## 4. Rate Limiting & Brute Force Protection

To mitigate brute-force password guessing attacks:
- The `/auth/login` endpoint is protected by `slowapi`.
- Rate limits default to **10 requests per minute per client IP** (`LOGIN_RATE_LIMIT = "10/minute"`).
- Requests exceeding the limit receive HTTP 429 (`Rate Limit Exceeded`).

---

## 5. Systemd Security Guidelines

When running Lavender as a systemd service, certain systemd sandbox flags must allow privilege escalation:

```ini
[Service]
# IMPORTANT: NoNewPrivileges must be disabled (no)
# If set to yes, sudo and PAM unix_chkpwd will fail to elevate privileges
NoNewPrivileges=no
```
