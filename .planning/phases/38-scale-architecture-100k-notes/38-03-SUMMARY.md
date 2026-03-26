---
phase: 38-scale-architecture-100k-notes
plan: "03"
subsystem: backup
tags: [backup, disaster-recovery, encryption, fernet]
dependency_graph:
  requires: []
  provides: [engine/backup.py, sb-backup CLI, sb-restore CLI, backup health check]
  affects: [engine/health.py, pyproject.toml]
tech_stack:
  added: [cryptography>=42.0 (Fernet)]
  patterns: [two-step confirm_token for destructive CLI ops, Fernet symmetric encryption, in-memory tar.gz]
key_files:
  created:
    - engine/backup.py
    - tests/test_backup.py
  modified:
    - engine/health.py
    - pyproject.toml
decisions:
  - "Fernet key stored at ~/.config/second-brain/backup.key (chmod 600) — consistent with CONFIG_PATH pattern"
  - "restore_main uses two-step confirm_token (secrets.token_hex(8), 60s expiry) — mirrors MCP destructive op pattern"
  - "backup_dir defaults to BRAIN_ROOT/.backup (not Drive-synced, local-only)"
  - "check_backup returns combined dict with sub-keys _backup and _key for granularity; CHECKS list gets single entry"
metrics:
  duration_seconds: 480
  completed_date: "2026-03-26"
  tasks_completed: 2
  files_changed: 4
---

# Phase 38 Plan 03: Encrypted Backup and Restore Summary

**One-liner:** Fernet-encrypted tar.gz backup of notes+DB+hnsw index with two-step CLI restore and sb-health staleness reporting.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Backup and restore module with tests | 88fddf1 | engine/backup.py, tests/test_backup.py, pyproject.toml |
| 2 | Wire backup into health check + register CLI entry points | 164bfc7 | engine/health.py, pyproject.toml |

## What Was Built

### engine/backup.py

Core functions:
- `_get_or_create_key()` — reads/generates Fernet key at `~/.config/second-brain/backup.key` with 0o600 permissions
- `backup_brain(brain_root, db_path, backup_dir)` — builds tar.gz in memory containing all `.md` files + brain.db + optional hnsw + label_map, encrypts with Fernet, writes to `backup_dir/brain-{timestamp}.enc`
- `restore_brain(enc_path, target_root, target_db)` — decrypts .enc file, extracts notes/db/hnsw to target paths, returns counts
- `check_backup_health(backup_dir, warn_days=7)` — finds newest .enc file, computes age, returns `{last_backup, stale, age_days}`
- `backup_main()` — `sb-backup` CLI entry point
- `restore_main()` — `sb-restore` CLI entry point with two-step confirm_token pattern

### engine/health.py

Added `check_backup()` function that:
- Calls `check_backup_health()` for staleness status
- Checks `KEY_PATH.exists()` for key presence
- Returns combined status (worst of backup + key)
- Appended to `CHECKS` list so it runs automatically with `sb-health`

### pyproject.toml

- Added `cryptography>=42.0` dependency (provides Fernet)
- Registered `sb-backup = "engine.backup:backup_main"`
- Registered `sb-restore = "engine.backup:restore_main"`

## Test Coverage

12 tests in `tests/test_backup.py`:
- `TestGetOrCreateKey`: creates with 0o600 perms, idempotent
- `TestBackupBrain`: creates .enc file, valid Fernet data
- `TestRestoreBrain`: extracts notes+DB, round-trip identical content, wrong key raises InvalidToken
- `TestCheckBackupHealth`: no backups, fresh backup not stale, old backup is stale
- `TestCLIEntryPoints`: backup_main callable smoke test, restore_main prints token

## Decisions Made

1. **Fernet key location:** `~/.config/second-brain/backup.key` (0o600) — consistent with existing CONFIG_PATH convention; outside brain folder so it's not in Drive sync or the backup itself.
2. **Two-step restore pattern:** `restore_main()` uses `secrets.token_hex(8)` with 60s expiry stored in module-level dict — mirrors MCP `_issue_token`/`_consume_token` pattern for destructive operations.
3. **backup_dir default:** `BRAIN_ROOT/.backup` — local-only (not Drive-synced), predictable location, created on first use.
4. **In-memory tar:** tar.gz built in `io.BytesIO` before Fernet encryption — avoids writing unencrypted intermediate files to disk.
5. **check_backup combined result:** Returns a single dict for the CHECKS list but includes sub-keys `_backup` and `_key` for granular programmatic access.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

Files verified:
- engine/backup.py: FOUND
- tests/test_backup.py: FOUND
- Commits 88fddf1 and 164bfc7: FOUND in git log
- `uv run pytest tests/test_backup.py -q`: 12 passed
