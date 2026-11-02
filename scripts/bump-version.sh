#!/usr/bin/env bash
# Usage: ./scripts/bump-version.sh 0.5.0
set -e
NEW_VERSION="${1:?Usage: $0 <new_version>}"

# pyproject.toml
sed -i "s/^version = \".*\"/version = \"${NEW_VERSION}\"/" pyproject.toml

# frontend/package.json
sed -i "s/\"version\": \".*\"/\"version\": \"${NEW_VERSION}\"/" frontend/package.json

# server/core/config.py
sed -i "s/APP_VERSION = \".*\"/APP_VERSION = \"${NEW_VERSION}\"/" server/core/config.py

echo "Bumped to ${NEW_VERSION}. Review the diff, update CHANGELOG.md, then commit."
