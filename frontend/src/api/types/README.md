# api/types/
TypeScript interfaces and types split by domain.
Each file covers one backend domain (auth, device, network, packages, etc.).

Rules:
- Only `interface`, `type`, and `enum` declarations.
- No logic, no imports from other src/ directories.
- Export all types as named exports.
- The legacy `api/types.ts` will be removed after all pages are migrated.

