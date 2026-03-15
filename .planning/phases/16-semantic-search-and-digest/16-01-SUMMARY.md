---
phase: 16-semantic-search-and-digest
plan: 01
subsystem: testing
tags: [tdd, pytest, semantic-search, digest, wave0, red-scaffold]

requires:
  - phase: 15-intelligence-layer
    provides: intelligence.py with _router, recap_main, check_connections, budget_available

provides:
  - 14 RED test stubs across 4 test files for Phase 16 behaviors
  - engine/digest.py stub module with generate_digest() and digest_main() raising NotImplementedError
  - sb-digest entry point registered in pyproject.toml

affects:
  - 16-02-search-implementation
  - 16-03-recap-entity-implementation
  - 16-04-digest-implementation

tech-stack:
  added: []
  patterns:
    - "Wave 0 RED scaffold: tests that import non-existent symbols fail with AttributeError/ImportError"
    - "pytest.raises(SystemExit) pattern for CLI flag stubs that haven't been added to argparse yet"
    - "generate_digest() call-then-assert pattern forces NotImplementedError to propagate as test failure"

key-files:
  created:
    - engine/digest.py
    - tests/test_digest.py
  modified:
    - tests/test_search.py
    - tests/test_intelligence.py
    - tests/test_read.py
    - pyproject.toml

key-decisions:
  - "TestDigestFlag/TestDigestFlagEmpty use pytest.raises(SystemExit) — engine.read.main() takes no args yet so TypeError propagates as RED"
  - "search_semantic/search_hybrid stubs use hasattr() assertion to produce cleaner failure message than bare AttributeError"
  - "recap_entity stubs use direct ImportError (no try/except) so Plan 03 GREEN state is unambiguous"

patterns-established:
  - "Wave 0 pattern: import non-existent symbol directly — ImportError/AttributeError is the RED signal"
  - "Digest test pattern: call generate_digest() then assert on result — NotImplementedError propagates as FAILED"

requirements-completed:
  - SRCH-01
  - SRCH-02
  - SRCH-03
  - SRCH-04
  - DIAG-01
  - DIAG-02
  - DIAG-03
  - DIAG-04

duration: 4min
completed: 2026-03-15
---

# Phase 16 Plan 01: Wave 0 RED Scaffold Summary

**14 failing test stubs across test_search.py, test_intelligence.py, test_digest.py, test_read.py; engine/digest.py stub with NotImplementedError stubs; sb-digest entry point registered**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-15T19:17:43Z
- **Completed:** 2026-03-15T19:21:45Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- 8 RED test stubs added to test_search.py and test_intelligence.py (TestSemanticSearch, TestSemanticFallback, TestHybridSearch, TestKeywordFlag, TestHybridFallback, TestRecapEntity, TestRecapEntityEmpty, TestRecapEntityPIIRouting)
- 6 RED test stubs added to test_digest.py and test_read.py (TestDigestWrite, TestDigestIdempotent, TestDigestSections, TestDigestPIIRouting, TestDigestFlag, TestDigestFlagEmpty)
- engine/digest.py created with generate_digest() and digest_main() stubs; sb-digest entry point registered in pyproject.toml

## Task Commits

1. **Task 1: Add failing test stubs to test_search.py and test_intelligence.py** - `4717adf` (test)
2. **Task 2: Create engine/digest.py stub, add test_digest.py + test_read.py stubs, register entry point** - `45f0422` (test)

## Files Created/Modified

- `engine/digest.py` - Stub module with generate_digest() and digest_main() raising NotImplementedError
- `tests/test_digest.py` - 4 RED test classes for digest generation (DIAG-01..04)
- `tests/test_search.py` - 5 RED test classes appended (SRCH-01..04 + hybrid fallback)
- `tests/test_intelligence.py` - 3 RED test classes appended (recap_entity behaviors)
- `tests/test_read.py` - 2 RED test classes appended (TestDigestFlag, TestDigestFlagEmpty)
- `pyproject.toml` - sb-digest entry point added

## Decisions Made

- TestDigestFlag/TestDigestFlagEmpty use `pytest.raises(SystemExit)` because `engine.read.main()` currently takes no arguments — the TypeError is sufficient to confirm RED state; Plan 04 must update both the flag and the tests.
- search_semantic/search_hybrid use `hasattr()` assertion before calling — gives explicit "not implemented" message instead of bare AttributeError.
- recap_entity stubs import directly (no try/except) so ImportError propagates as unambiguous RED.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- All 14 RED test classes are in place; Plans 02, 03, and 04 can independently drive each to GREEN.
- engine/digest.py is importable and sb-digest entry point is registered.
- 30 pre-existing tests remain GREEN — no regressions introduced.

---
*Phase: 16-semantic-search-and-digest*
*Completed: 2026-03-15*
