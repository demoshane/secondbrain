---
phase: 12-micro-code-fixes
plan: "01"
subsystem: cli
tags: [argparse, pyproject, entry-points, gdpr, ai-layer]

# Dependency graph
requires:
  - phase: 12-micro-code-fixes
    provides: Wave 0 RED tests confirming missing entry points (12-00)
  - phase: 11-gdpr-scope-expansion
    provides: engine.anonymize:main() already implemented
  - phase: 08-fix-update-memory-routing
    provides: engine.ai.update_memory() via ModelRouter
provides:
  - sb-anonymize CLI entry point registered in pyproject.toml
  - sb-update-memory CLI entry point registered in pyproject.toml
  - engine/ai.py main() argparse wrapper with --note-type, --summary, --config-path
affects: [gdpr-tooling, ai-layer, cli-surface]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy import of BRAIN_ROOT inside main() — consistent with engine/ pattern"
    - "argparse main() wrapper added at module bottom with if __name__ == '__main__' guard"

key-files:
  created: []
  modified:
    - pyproject.toml
    - engine/ai.py

key-decisions:
  - "sb-anonymize entry point wired to engine.anonymize:main (already existed — no new code needed)"
  - "sb-update-memory entry point wired to engine.ai:main (new main() added)"
  - "config_path defaults to BRAIN_ROOT/.meta/config.toml matching other main() patterns in engine/"

patterns-established:
  - "argparse main() wrapper: lazy import BRAIN_ROOT, Path(args.config_path) or default sentinel"

requirements-completed: [GDPR-03, AI-06]

# Metrics
duration: 2min
completed: 2026-03-15
---

# Phase 12 Plan 01: Micro Code Fixes — CLI Entry Points Summary

**sb-anonymize and sb-update-memory registered as shell-callable CLI entry points; engine/ai.py gains argparse main() wrapper with --note-type, --summary, --config-path**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-15T12:00:33Z
- **Completed:** 2026-03-15T12:01:04Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added `sb-anonymize = "engine.anonymize:main"` and `sb-update-memory = "engine.ai:main"` to pyproject.toml [project.scripts]
- Reinstalled package with `uv pip install -e .` to register entry points in environment
- Added `main()` argparse function to engine/ai.py with three CLI arguments: `--note-type`, `--summary`, `--config-path`
- All 15 tests in test_anonymize.py and test_ai.py pass; full suite 148 passed, 5 skipped, 1 xfailed

## Task Commits

Each task was committed atomically:

1. **Task 1: Add sb-anonymize and sb-update-memory to pyproject.toml** - `33555b2` (feat)
2. **Task 2: Add main() wrapper to engine/ai.py** - `48e774c` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `pyproject.toml` - Added sb-anonymize and sb-update-memory to [project.scripts]
- `engine/ai.py` - Appended main() argparse wrapper and if __name__ == '__main__' guard

## Decisions Made
- sb-anonymize required no new code — engine.anonymize:main() was already implemented in Phase 11; only pyproject.toml wiring was missing
- config_path default inside main() uses `BRAIN_ROOT / ".meta" / "config.toml"` — matches capture.py/read.py pattern, lazy import avoids circular import risk

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- GDPR-03 and AI-06 requirements closed
- sb-anonymize and sb-update-memory are shell-callable; `sb-anonymize --help` and `sb-update-memory --help` both run without error
- Plan 12-02 (or remaining micro-fix plans) can proceed

---
*Phase: 12-micro-code-fixes*
*Completed: 2026-03-15*
