---
phase: 17-api-layer-and-setup-automation
plan: "02"
subsystem: infra
tags: [ollama, google-drive, setup, init, macos, windows, auto-detect]

requires:
  - phase: 17-00
    provides: RED scaffold tests for SETUP-01 through SETUP-04

provides:
  - detect_drive_macos() in engine/init_brain.py
  - detect_drive_windows() in engine/init_brain.py
  - detect_drive_path() in engine/init_brain.py
  - assert_drive_or_exit() in engine/init_brain.py
  - ollama_ensure() in engine/init_brain.py
  - ollama_model_size_warning() in engine/init_brain.py
  - --detect-drive CLI flag in sb-init

affects: [phase 18-gui, phase 17-03]

tech-stack:
  added: []
  patterns:
    - "Drive detection uses platform dispatch (sys.platform) to macOS glob or Windows GFS/drive-letter scan"
    - "ollama SDK used for model list check; subprocess fallback if SDK unavailable"
    - "assert_drive_or_exit accepts base_path kwarg for test isolation without monkeypatching Path.home"

key-files:
  created: []
  modified:
    - engine/init_brain.py

key-decisions:
  - "assert_drive_or_exit takes base_path kwarg (not home) to match test scaffold signature"
  - "ollama_model_size_warning uses ollama Python SDK ollama.list() — not subprocess — to match test scaffold"
  - "Size warning prints ~800 MB (not ~274 MB from plan) to match test assertion in scaffold"

patterns-established:
  - "Test scaffold drives implementation contract — when RED tests and plan spec differ, tests win"

requirements-completed: [SETUP-01, SETUP-02, SETUP-03, SETUP-04]

duration: 8min
completed: 2026-03-15
---

# Phase 17 Plan 02: Drive Auto-Detection and Ollama Setup Summary

**Six new functions turn sb-init into zero-config setup: Drive auto-detected via macOS CloudStorage glob or Windows GFS/drive-letter scan; Ollama installed via brew/winget or gracefully degraded with download URL.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-15T20:10:00Z
- **Completed:** 2026-03-15T20:18:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- `detect_drive_macos()` globs `~/Library/CloudStorage/GoogleDrive-*/My Drive` for Drive path
- `detect_drive_windows()` checks `~/GFS/My Drive` then scans G-Z drive letters
- `assert_drive_or_exit()` exits non-zero with human-readable error if Drive not found
- `ollama_ensure()` installs Ollama via brew (macOS) or winget (Windows); returns False + URL when no package manager
- `ollama_model_size_warning()` uses ollama SDK to detect missing model; prints ~800 MB warning before pull
- `main()` wired: `--detect-drive` flag + ollama check after schema init

## Task Commits

1. **Task 1: Add Drive detection and Ollama functions** - `a34bffa` (feat)

## Files Created/Modified

- `engine/init_brain.py` - Added 6 new functions + main() wiring; 131 lines added

## Decisions Made

- `assert_drive_or_exit` uses `base_path` kwarg instead of `home` — test scaffold calls `assert_drive_or_exit(base_path=tmp_path)` so implementation must match that signature
- `ollama_model_size_warning` uses `ollama` Python SDK (`ollama.list()`) not subprocess — test patches `ollama.list` directly
- Size warning prints `~800 MB` not `~274 MB` — test asserts `"800 MB" in output`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Adapted function signatures and size constant to match RED test scaffold**
- **Found during:** Task 1 analysis
- **Issue:** Plan spec said `assert_drive_or_exit(home=None)` and `~274 MB`; test scaffold calls `assert_drive_or_exit(base_path=tmp_path)` and asserts `"800 MB"`
- **Fix:** Used `base_path` kwarg with platform-dispatch fallback; printed `~800 MB` in size warning
- **Files modified:** engine/init_brain.py
- **Verification:** All 13 test_init_brain tests pass GREEN
- **Committed in:** a34bffa

---

**Total deviations:** 1 auto-fixed (signature + constant mismatch between plan and RED scaffold)
**Impact on plan:** Necessary for GREEN state — test scaffold is the authoritative contract.

## Issues Encountered

Pre-existing failure in `tests/test_precommit.py::test_blocks_api_key` (detect-secrets tool behavior) — unrelated to this plan, not introduced by these changes.

## Next Phase Readiness

- SETUP-01 through SETUP-04 requirements satisfied
- engine/init_brain.py ready for Phase 17-03 or further extension
- No blockers

---
*Phase: 17-api-layer-and-setup-automation*
*Completed: 2026-03-15*
