# Postfix Lint Report

After running `uv run ruff check server/ --fix`, 16 errors remain across 4 rules:

## E402: Module Import Not at Top of File

**Count:** 10

**Examples:**
- `server/api/live.py:109`
- `server/api/live.py:111`
- `server/api/live.py:112`
- `server/api/system.py:131`
- `server/services/live.py:31`
- `server/services/live.py:32`
- `server/services/live.py:40`
- `server/services/live.py:41`
- `server/services/live.py:42`
- `server/services/live.py:47`

## E741: Ambiguous Variable Name

**Count:** 4

**Examples:**
- `server/services/packages.py:119`
- `server/services/packages.py:236`
- `server/services/packages.py:388`
- `server/services/packages.py:497`

## F821: Undefined Name

**Count:** 1

**Example:**
- `server/services/battery.py:351`

## F841: Unused Variable

**Count:** 1

**Example:**
- `server/services/systemd.py:89`

## Summary

Total remaining errors: 16

These issues require manual attention to resolve.