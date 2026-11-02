#!/usr/bin/env bash
# Usage: ./scripts/bump-version.sh 0.5.1
set -e

NEW_VERSION="${1:?Usage: $0 <new_version>}"

# Validate SemVer format: X.Y.Z or X.Y.Z-prerelease
if [[ ! "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$ ]]; then
  echo "Error: Version '$NEW_VERSION' is not valid SemVer (expected format: X.Y.Z or X.Y.Z-prerelease)" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Bumping Lavender version to: ${NEW_VERSION}"

# 1. pyproject.toml
sed -i "s/^version = \".*\"/version = \"${NEW_VERSION}\"/" "$ROOT_DIR/pyproject.toml"

# 2. frontend/package.json
sed -i "s/\"version\": \".*\"/\"version\": \"${NEW_VERSION}\"/" "$ROOT_DIR/frontend/package.json"

# 3. server/core/config.py
sed -i "s/APP_VERSION = \".*\"/APP_VERSION = \"${NEW_VERSION}\"/" "$ROOT_DIR/server/core/config.py"

# 4. server/__init__.py
sed -i "s/__version__ = \".*\"/__version__ = \"${NEW_VERSION}\"/" "$ROOT_DIR/server/__init__.py"

# 5. docs/configuration.md
sed -i "s/| \`APP_VERSION\` | \".*\" |/| \`APP_VERSION\` | \"${NEW_VERSION}\" |/" "$ROOT_DIR/docs/configuration.md"

# 6. uv.lock (if uv is available)
if command -v uv &>/dev/null; then
  (cd "$ROOT_DIR" && uv lock --quiet 2>/dev/null) || true
fi

echo "Version files updated successfully to ${NEW_VERSION}."
echo "Next steps:"
echo "  1. Review changes: git diff"
echo "  2. Update CHANGELOG.md with release notes"
echo "  3. Commit: git commit -am \"chore(release): bump version to ${NEW_VERSION}\""
