/**
 * Frontend configuration and feature toggles for Lavender Dashboard.
 */

/**
 * Toggle whether the root homepage ('/' - Overview) requires user authentication.
 *
 * - false (default): The homepage is completely public and can be viewed without logging in.
 *   Telemetry, hardware graphs, resource statistics, system logs, and storage stats are visible.
 *   All execution and modification capabilities (services, processes, storage explorer, network,
 *   packages, users, power) remain strictly guarded behind session authentication.
 * - true: The homepage is locked down and requires user login before any views can be accessed.
 *
 * Note: Lavender also synchronizes this setting with the FastAPI backend configuration
 * `REQUIRE_AUTH_FOR_HOMEPAGE` in `server/core/config.py` (or `LAVENDER_REQUIRE_AUTH_FOR_HOMEPAGE` env var).
 */
export const REQUIRE_AUTH_FOR_HOMEPAGE = false;
