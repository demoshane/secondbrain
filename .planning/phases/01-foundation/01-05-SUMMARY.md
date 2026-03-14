---
phase: 01-foundation
plan: "05"
subsystem: infra
tags: [bootstrap, validator, pathlib, static-analysis, tdd]

# Dependency graph
requires:
  - phase: 01-foundation/01-03
    provides: engine/paths.py with BRAIN_ROOT, INDEX_ROOT, DB_PATH, BRAIN_SUBDIRS
  - phase: 01-foundation/01-04
    provides: engine/reindex.py completed engine package

provides:
  - scripts/bootstrap.py — host-side environment validator with check-all pattern
  - tests/test_bootstrap.py — 4 tests covering check-all, pass/fail output, dev flag, check labels
  - tests/test_paths.py — 4 tests including static analysis for no os.path.join and no hardcoded paths in engine/

affects: [devcontainer-setup, phase-02, fresh-install-docs]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "@check decorator pattern for registering named checks — list-based, check-all (not fail-fast)"
    - "TDD with importlib.util.spec_from_file_location for loading scripts outside package structure"
    - "Static analysis tests using rglob + string search (no AST needed for simple pattern enforcement)"

key-files:
  created:
    - scripts/bootstrap.py
    - scripts/__init__.py
    - tests/test_bootstrap.py
    - tests/test_paths.py
  modified: []

key-decisions:
  - "bootstrap.py runs on HOST (not container) — uses Path.home() directly, no engine.paths import"
  - "check-all pattern: all checks always run, results collected, single exit at end"
  - "test_paths.py enforces FOUND-12 via static analysis (rglob + string search) — not just convention"

patterns-established:
  - "@check(label) decorator: registers (label, fn) tuples in module-level _checks list"
  - "Static analysis in tests: rglob('*.py') + read_text() + assert 'banned_string' not in content"

requirements-completed: [FOUND-10, FOUND-11, FOUND-12]

# Metrics
duration: 1min
completed: 2026-03-14
---

# Phase 1 Plan 05: Bootstrap Validator Summary

**Host-side environment validator with @check decorator pattern, check-all semantics, [PASS]/[FAIL] output, and enforced pathlib-only policy in engine/ via static analysis tests**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-03-14T13:16:42Z
- **Completed:** 2026-03-14T13:17:22Z
- **Tasks:** 2 (TDD: RED commit + GREEN commit per task set)
- **Files modified:** 4

## Accomplishments

- scripts/bootstrap.py implements check-all validator: Drive folder writable, .env.host present, python-frontmatter installed, Python >= 3.12; Windows host prints WSL2 warning
- 4 bootstrap tests cover: [PASS]/[FAIL] output, check-all (no fail-fast), --dev flag, check label presence in output
- 4 paths static-analysis tests enforce FOUND-12: no os.path.join in engine/, no hardcoded /workspace/brain outside paths.py, engine file existence, paths.py symbol exports

## Task Commits

Each task was committed atomically:

1. **Task 1+2 RED: Failing tests** - `1016223` (test)
2. **Task 1 GREEN: bootstrap.py implementation** - `ee7baeb` (feat)

_Note: TDD tasks committed as RED (tests) then GREEN (implementation). Both test files written together in RED phase since they are interdependent with the same implementation target._

## Files Created/Modified

- `scripts/bootstrap.py` - Host-side environment validator with @check decorator, check-all pattern, [PASS]/[FAIL] output, exit 0/1
- `scripts/__init__.py` - Empty package marker for scripts/
- `tests/test_bootstrap.py` - 4 tests: check-all semantics, pass/fail output, --dev flag, check labels in output
- `tests/test_paths.py` - 4 tests: engine file existence, no os.path.join in engine/, no hardcoded /workspace/brain outside paths.py, paths.py symbol exports

## Decisions Made

- bootstrap.py runs on the HOST (not inside container) — uses Path.home() directly rather than importing engine.paths (which has /workspace/brain paths only valid inside container)
- check-all pattern: all checks always run regardless of failures; single sys.exit() at the end after collecting all results
- FOUND-12 enforced by static analysis tests (rglob + string search) — makes the convention a hard test failure, not just documentation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Pre-existing `test_reindex.py` collection error (missing `frontmatter` module in bare uv env without --with python-frontmatter) — not caused by this plan's changes. Tests for this plan pass cleanly in isolation and in full suite excluding that file (25 passed, 2 skipped).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 1 foundation complete: devcontainer config, engine package (paths/db/init_brain/reindex), pre-commit hooks, bootstrap validator
- Fresh install entry point (bootstrap.py --dev) ready for use
- Static analysis enforcement (test_paths.py) in place for pathlib-only policy
- Phase 2 can proceed — all engine infrastructure in place

---
*Phase: 01-foundation*
*Completed: 2026-03-14*
