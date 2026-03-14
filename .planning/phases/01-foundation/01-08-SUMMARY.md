---
phase: 01-foundation
plan: "08"
subsystem: infra
tags: [bootstrap, uv, venv, documentation]

requires: []
provides:
  - README.md bootstrap invocation uses `uv run python scripts/bootstrap.py --dev`
  - bootstrap.py warns users who invoke with bare python outside a virtualenv
affects: [onboarding, devcontainer-setup]

tech-stack:
  added: []
  patterns:
    - "Venv guard: check sys.prefix == sys.base_prefix at top of main() to catch bare-python invocations"

key-files:
  created: []
  modified:
    - README.md
    - scripts/bootstrap.py

key-decisions:
  - "Venv guard placed before first check so warning is immediately visible even if --dev flag is missing"

patterns-established:
  - "CLI entry points in scripts/ should guard against bare-python invocations via sys.prefix check"

requirements-completed: [FOUND-07]

duration: 1min
completed: 2026-03-14
---

# Phase 1 Plan 08: Fix Bootstrap Invocation Documentation Summary

**README and bootstrap.py updated to use `uv run` invocation; venv guard added to warn bare-python users before any checks run**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-14T14:48:44Z
- **Completed:** 2026-03-14T14:49:27Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- README.md now instructs users to run `uv run python scripts/bootstrap.py --dev`
- bootstrap.py docstring corrected to match
- Venv guard in main() prints three [WARN] lines if invoked with bare python outside a virtualenv

## Task Commits

1. **Task 1: Update README.md invocation line** - `288c9ef` (docs)
2. **Task 2: Fix bootstrap.py docstring and add venv guard** - `4819d19` (fix)

## Files Created/Modified

- `README.md` - Changed bare `python scripts/bootstrap.py --dev` to `uv run python scripts/bootstrap.py --dev`
- `scripts/bootstrap.py` - Updated docstring invocation example; added venv guard using `sys.prefix == sys.base_prefix`

## Decisions Made

- Venv guard placed at start of main() (after arg parsing, before checks) so warning is visible even if the user forgets `--dev`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Bootstrap invocation is now correct in all documentation and enforced at runtime
- Plan 09 (if any) can proceed — no blockers from this plan

---
*Phase: 01-foundation*
*Completed: 2026-03-14*
