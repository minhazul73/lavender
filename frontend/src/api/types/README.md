# api/types/
TypeScript interfaces and types split by domain.
Each file covers one backend domain (auth, device, network, packages, etc.).

Rules:
- Only `interface`, `type`, and `enum` declarations.
- No logic, no imports from other src/ directories.
- Export all types as explicit named exports (no wildcard re-exports).
- Legacy `api/types.ts` barrel file removed; all consumers import directly from domain type files.

