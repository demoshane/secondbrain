---
phase: 37-housekeeping
plan: 08
status: complete
---

# 37-08 Summary — Drive sync health check + setup.sh guidance

## What was done
Added Google Drive sync detection to `sb-health` and `setup.sh`. Prerequisite for Phase 38 backup.

## Changes
- `engine/brain_health.py`: Added `check_drive_sync()` with 3-tier detection (not_installed → not_running → ok/not_configured). Integrated into `get_brain_health_report()` as `drive_sync` key.
- `tests/test_brain_health.py`: 5 new tests — 4 for the 4 Drive sync tiers, 1 for health report integration.
- `setup.sh`: Added "Checking Google Drive sync" step (step 8) between reindex and health check — detects installed/running state, shows guidance if missing.

## Verification
- `uv run pytest tests/test_brain_health.py -q -k drive` — 5 passed
- `uv run pytest tests/test_brain_health.py` — 30 passed, 7 xpassed
- `bash -n setup.sh` — no syntax errors
- `grep -c "Google Drive" setup.sh` — 10 occurrences
