# `dashboard/main.py` — static asset caching

**Purpose:** FastAPI app entrypoint, middleware, static file serving.

## Key changes

- **Cache-busting.** Git hash injected into static asset URLs
  (`/static/...?v=<githash>`) so new deploys are picked up without users holding
  stale CSS/JS.
- **`Cache-Control: no-cache` middleware** on static files to prevent stale
  caches at the browser level.

## Performance improvements

- Correct cache semantics: browsers revalidate instead of silently serving
  stale bundles (fixes the "UI looks broken after deploy" class of bugs; not a
  raw-speed change).

## Usage

The asset hash is injected by the FastAPI application setup. In the current
React SPA build, hashed bundles are referenced directly in the SPA's HTML
entry point:

```html
<link rel="stylesheet" href="/static/css/main.<hash>.css">
<script src="/static/js/main.<hash>.js"></script>
```

The legacy Jinja2 templates in `dashboard/templates/` also inject the hash via
`url_for`, but the SPA is the primary UI.

## Caveats

- **Client-side caching.** `no-cache` ensures revalidation, but actual download
  of new assets still occurs on deploy. For large assets, consider `Cache-Control:
  max-age=...` with aggressive caching and a different cache-busting strategy
  (e.g., content hashing in filenames) if zero revalidation delay is critical.
- **CDN compatibility.** `no-cache` works correctly with CDNs, forcing them to
  revalidate their cache against the origin.

## Code references

- `dashboard/main.py` — asset hash injection + `no-cache` middleware

## Benchmarks

None recorded. See the parent doc
[`docs/optimized-modules.md`](../optimized-modules.md#verification) for how to
produce real numbers.
