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
- When startup seeds `dev-session-active`, a request without `rn7_session` from `127.0.0.1`, `localhost`, or `::1` uses that administrator session.
- This fallback depends on the client address received by the application. Review proxy and deployment settings to ensure remote requests cannot receive a loopback client address unintentionally.

### 3. Cockpit-Style Administrative Elevation
- `/auth/elevate` validates the supplied password with `sudo -v` without checking the session user's groups, then marks the requesting session as elevated.
- The session elevation flag expires after 15 minutes (`ADMIN_ELEVATION_TIMEOUT_MINUTES`). This setting does not set the sudo timestamp lifetime.
- Revoking elevation (`/auth/drop-admin`) immediately invalidates the session elevation flag and executes `sudo -k` on the host.

### 4. Rate Limiting
- Login requests are rate-limited to 10 attempts per minute (`LOGIN_RATE_LIMIT`) using `slowapi` to defend against brute-force attacks.
