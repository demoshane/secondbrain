---
phase: 11-gdpr-scope-expansion
plan: "00"
subsystem: testing
tags: [gdpr, xfail, stubs, tdd, export, anonymize, consent]

requires:
  - phase: 05-gdpr-and-maintenance
    provides: forget_person, read_note patterns and deferred-import xfail convention

provides:
  - 4 xfail stubs in tests/test_export.py (GDPR-02 export contract)
  - 6 xfail stubs in tests/test_anonymize.py (GDPR-03 anonymize contract)
  - 5 xfail stubs in tests/test_consent.py (GDPR-06 consent contract)
  - engine/export.py with export_brain() and main() stubs
  - engine/anonymize.py with anonymize_note() and main() stubs
  - engine/init_brain.py consent helpers: check_consent, write_consent_sentinel, prompt_consent (stub)
  - engine/init_brain.py --yes argparse flag for non-interactive CI use
  - pyproject.toml sb-export entry point wired to engine.export:main

affects:
  - 11-01 (implement export_brain)
  - 11-02 (implement anonymize_note)
  - 11-03 (implement prompt_consent and wire --yes flag)

tech-stack:
  added: []
  patterns:
    - "Deferred import inside xfail test body — consistent with Phase 5 and Phase 6 pattern"
    - "Wave 0 RED baseline: all stubs xfail (strict=False) so later waves upgrade to passing"

key-files:
  created:
    - tests/test_export.py
    - tests/test_anonymize.py
    - tests/test_consent.py
    - engine/export.py
    - engine/anonymize.py
  modified:
    - engine/init_brain.py
    - pyproject.toml

key-decisions:
  - "Deferred import pattern inside xfail bodies ensures --collect-only works before any module is implemented (consistent with Phase 5 decision)"
  - "prompt_consent() is a stub (NotImplementedError) in Wave 0 — wiring to main() deferred to plan 11-03"
  - "sb-export entry point wired in pyproject.toml at Wave 0 so later implementation plans need no toml edits"

patterns-established:
  - "Wave 0 stubs use xfail(strict=False) — upgradeable to plain passing tests in later waves without test file rewrites"

requirements-completed: [GDPR-02, GDPR-03, GDPR-06]

duration: 2min
completed: 2026-03-15
---

# Phase 11 Plan 00: GDPR Scope Expansion Wave 0 Summary

**15 xfail test stubs (export/anonymize/consent) plus NotImplementedError module stubs establishing RED baseline for GDPR-02, GDPR-03, GDPR-06**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-15T11:05:28Z
- **Completed:** 2026-03-15T11:07:25Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- 15 xfail stubs across 3 test files collected without error (deferred-import pattern)
- 2 new stub modules (engine/export.py, engine/anonymize.py) importable without error
- engine/init_brain.py extended with check_consent, write_consent_sentinel, prompt_consent stub, and --yes flag
- sb-export entry point registered in pyproject.toml
- Full test suite passes with no regressions (all 15 new tests xfail as intended)

## Task Commits

1. **Task 1: Test stubs — test_export.py, test_anonymize.py, test_consent.py** - `b8310f7` (test)
2. **Task 2: Module stubs — engine/export.py, engine/anonymize.py, init_brain.py, pyproject.toml** - `7d8b70c` (feat)

## Files Created/Modified

- `tests/test_export.py` - 4 xfail stubs for GDPR-02 export contract
- `tests/test_anonymize.py` - 6 xfail stubs for GDPR-03 anonymize contract
- `tests/test_consent.py` - 5 xfail stubs for GDPR-06 consent contract
- `engine/export.py` - export_brain() and main() stubs (NotImplementedError)
- `engine/anonymize.py` - anonymize_note() and main() stubs (NotImplementedError)
- `engine/init_brain.py` - added CONSENT_NOTICE, CONSENT_PATH_RELATIVE, check_consent(), write_consent_sentinel(), prompt_consent() stub, --yes argparse flag
- `pyproject.toml` - added sb-export = "engine.export:main" entry point

## Decisions Made

- Deferred import inside each test body (consistent with Phase 5 pattern) ensures `--collect-only` works before modules are implemented
- `prompt_consent()` left as `NotImplementedError` stub — full implementation and wiring to `main()` is plan 11-03 scope
- `sb-export` wired at Wave 0 so plans 11-01/11-02/11-03 need no pyproject.toml edits

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Wave 0 RED baseline established — plans 11-01 (export), 11-02 (anonymize), 11-03 (consent) can now implement against this contract
- All 15 stub tests will upgrade from xfail to passing as each wave implements the corresponding module
- Full suite clean: no regressions introduced

---
*Phase: 11-gdpr-scope-expansion*
*Completed: 2026-03-15*
