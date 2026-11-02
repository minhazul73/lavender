# AGENTS.md — Lavender Project Conventions

Read this file before making any code changes. These rules apply to every
AI-assisted task in this repository.

## Project Overview
Lavender is a FastAPI + React Linux system dashboard. Backend: Python 3.11+,
FastAPI, Pydantic v2. Frontend: React 18, TypeScript, Vite, Vanilla CSS.

## General Rules
- Touch ONLY the files listed in your task's `## Files` section.
- The project must build and run after every commit. Never leave it broken.
- Moved code must be verbatim — same logic, variable names, comments.
- Separate refactors from bug fixes in separate commits.
- Never add `console.log`, `print()`, or debug statements unless the task
  requires them.
- Never commit secrets, credentials, or personal data.

## Backend (Python)
- **Target file size:** 250 lines max. Files over 300 lines are flagged "large".
- **One responsibility per file:** collector, service, schema, util, or router.
- **Import direction:** `api/ → services/ → utils/ → core/`. Never import
  `api/` from `services/` or lower layers.
- **Naming:** `snake_case` for modules and functions, `PascalCase` for classes.
- **Async:** Use `asyncio.create_subprocess_exec` never `create_subprocess_shell`.
- **Config:** All env vars must be read in `server/core/config.py`.
- **Executor:** Use `get_executor()` from `server.core.executor` for subprocess
  calls, not raw `subprocess.run` or `asyncio.create_subprocess_*` directly.
- **Tests:** `uv run pytest tests/ -v --timeout=60` must pass after every change.

## Frontend (TypeScript / React)
- **Target file size:** 250 lines max per `.tsx`/`.ts` file.
- **One responsibility per file:** a file is either a component, a hook, a
  service/API function, a utility, a type definition, or a constant set.
- **Naming:** `PascalCase` for components/types, `camelCase` for
  hooks/utils/functions, `UPPER_SNAKE` for constants, `kebab-case` for CSS.
- **Import direction:** `pages/ → hooks/ → api/ → utils/ → types/`.
  Never import a page from a hook or util.
- **No barrel files:** Do not create `index.ts` re-exports. Import directly
  from the source file.
- **No direct fetch in components:** API calls must go through `api/client.ts`
  or a custom hook. Components must not contain raw `fetch()` calls.
- **CSS:** Vanilla CSS with custom properties. No Tailwind, no inline styles
  for layout (component-scoped inline styles for dynamic values are OK).
- **Tests:** `cd frontend && bun run typecheck && bun run test` must pass.

## File Locations
| What | Where |
|---|---|
| Shared TS types | `frontend/src/api/types/` (split by domain) |
| Custom React hooks | `frontend/src/hooks/` |
| Pure TS utilities | `frontend/src/utils/` |
| Constants | `frontend/src/constants/` |
| API client functions | `frontend/src/api/client.ts` |
| Backend services | `server/services/` |
| Backend utilities | `server/utils/` |
| Pydantic schemas | `server/schemas/` |
| Backend config | `server/core/config.py` |

## Commit Message Format
Follow Conventional Commits: `type(scope): short description`

Types: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`, `style`, `ci`

Examples:
- `fix(security): remove shell execution path from auth bridge`
- `refactor(overview): extract sparkline utils to utils/sparkline.ts`
- `docs(onboarding): add .env.example with all configuration variables`
