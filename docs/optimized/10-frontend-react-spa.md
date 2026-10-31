# Frontend cutover: React SPA (`frontend/`, Phase 3–4)

**Purpose:** Replace the Jinja2 + vanilla-JS UI with a Vite + React + TS SPA
to make the dashboard maintainable.

## Key changes

- **Scaffold.** Vite + React + TS, auth, theme, test suite.
- **Phase 3:** all dashboard pages migrated (in the companion repo).
- **Phase 4 cutover:** Jinja2 will be removed and the SPA served by the
  FastAPI backend. The companion repository owns the SPA work; Phase 4 also
  requires backend changes in this repository.
- **SSE hook optimization** (see [`06-sse-transport.md`](06-sse-transport.md)).

## Performance / resource improvements

- Bundled, minified assets served from one build (vs many hand-maintained
  templates + 3 global JS/CSS files); dev builds cached by Vite.
- Per-page component split means a page change rebuilds/loads only its chunk.

## Usage

**This module lives in the companion `lavender-react` repository, not in this
codebase.** The FastAPI backend in this repo still serves the legacy Jinja2 +
vanilla-JS UI (`dashboard/templates/`, `dashboard/static/`) while the React
SPA is under development. See the note in `docs/architecture.md` §1.

Developers work within the `frontend/src/` directory of the companion repo,
using standard React, TypeScript, and Vite workflows.

**Key entry points:**
- `frontend/src/main.tsx`: React app entry
- `frontend/src/App.tsx`: Main application layout and routing
- `frontend/src/pages/`: Individual dashboard pages
- `frontend/src/components/`: Reusable UI components

## Caveats

- **Build step.** Unlike the previous Jinja2 approach, the React UI requires a
  build step (`bun run build` or `npm run build`) before deployment to generate
  the static assets served by FastAPI.
- **`bun` dependency.** The `frontend/` project is built with `bun`.
  Ensure `bun` is installed and configured in the PATH.
- **`useSSE` hook.** The SSE logic has been migrated and optimized into a React
  hook (`frontend/src/hooks/useSSE.ts`) for easier consumption by components.
- **Not yet live.** Until the Phase 4 cutover lands in this backend, the SPA is
  not the UI a user sees; `dashboard/templates/` remains the current UI.

## Code references

- `frontend/src/` — SPA source (companion repo)
- `frontend/src/hooks/useSSE.ts` — SSE hook
- `frontend/src/pages/Overview/OverviewPage.tsx` — sparkline buffering

## Benchmarks

None recorded. See the parent doc
[`docs/optimized-modules.md`](../optimized-modules.md#verification) for how to
produce real numbers.
