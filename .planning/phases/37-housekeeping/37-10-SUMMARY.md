---
plan: 37-10
status: complete
---

## Changes

- `engine/health.py`: added `check_drive_sync_health()` wrapper that calls `brain_health.check_drive_sync()` and maps its 3-tier status (ok/not_running/other) to health.py's {label, status, detail} format. Appended to CHECKS list.

## Outcome

`sb-health` now shows a "Drive sync" line. Status maps: `ok` → green tick, `not_running` → warning, anything else → fail.
