# Authentication & Security Architecture

Lavender interfaces directly with the host Linux operating system's authentication and authorization subsystems. It avoids storing passwords or creating secondary database accounts.

## Core Security Features

### 1. Multi-Stage Linux Credential Verification
When a user authenticates via `/auth/login`, credentials are verified sequentially:
1. **Direct Shadow Verification:** Attempts reading `/etc/shadow` using `spwd` and `crypt` (if the process has read permissions).
2. **Linux PAM Services:** Tries authentication against PAM services (`PAM_SERVICE` config, `base-auth`, `login`, `other`, `common-auth`, `system-auth`, `sudo`).
3. **Sudo Validation:** Invalidates cached credentials (`sudo -k`), then verifies via `sudo -S -p '' -v`.
4. **Doas Validation:** Evaluates permissions via `doas -C /etc/doas.conf true` (common on Alpine Linux and postmarketOS).

### 2. Signed Cookie Session Management
- Sessions are stored in-memory in `SessionStore`.
- The session identifier is cryptographically signed using `itsdangerous.URLSafeSerializer` with a configurable secret key (`DASHBOARD_SECRET_KEY`).
- Issued cookies (`rn7_session`) are marked `HttpOnly`, `SameSite=Lax`, and given a 60-minute sliding idle timeout (`SESSION_MAX_IDLE_MINUTES`).
- A background task purges inactive sessions every 5 minutes.

### 3. Cockpit-Style Administrative Elevation
- Users in administrative groups (`wheel`, `sudo`, `root` or `UID 0`) can elevate their session privileges by re-entering their password at `/auth/elevate`.
- Elevation issues a temporary 15-minute timestamp ticket (`ADMIN_ELEVATION_TIMEOUT_MINUTES`) via `sudo -v`.
- Revoking elevation (`/auth/drop-admin`) immediately invalidates the session elevation flag and executes `sudo -k` on the host.

### 4. Rate Limiting
- Login requests are rate-limited to 10 attempts per minute (`LOGIN_RATE_LIMIT`) using `slowapi` to defend against brute-force attacks.
