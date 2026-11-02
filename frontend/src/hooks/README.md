# hooks/
Custom React hooks. Each file exports exactly one hook.

Rules:
- File name matches hook name: `useClipboard.ts` exports `useClipboard`.
- Hooks may call `api/client.ts` but must not contain JSX.
- Hooks must not import from `pages/`.
- Keep under 150 lines. If larger, split into sub-hooks.

