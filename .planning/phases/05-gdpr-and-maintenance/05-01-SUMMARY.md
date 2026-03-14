---
phase: 05-gdpr-and-maintenance
plan: "01"
subsystem: database
tags: [sqlite, fts5, gdpr, erasure, pathlib, python-frontmatter]

requires:
  - phase: 05-00
    provides: engine/forget.py stub, sb-forget entry point wired in pyproject.toml, test_forget.py xfail stubs

provides:
  - forget_person() full GDPR erasure cascade (delete person file, sole-reference meetings, backlinks, DB rows, FTS5 rebuild)
  - main() CLI entry point for sb-forget
  - _fts5_query() phrase-quoting helper in engine/search.py preventing hyphenated-slug OperationalError

affects: [05-02, 05-03, any plan that calls search_notes with hyphenated queries]

tech-stack:
  added: []
  patterns:
    - "Exact-path DB deletion (not LIKE) for GDPR erasure — Pitfall 5 avoidance"
    - "FTS5 explicit rebuild after every forget_person() call — GDPR-02 mandatory"
    - "SpyConnection subclass for sqlite3 execute spy — Python 3.14 conn.execute is read-only"
    - "FTS5 phrase-quoting via _fts5_query() — wraps user query in double-quotes, escapes internal quotes"

key-files:
  created: []
  modified:
    - engine/forget.py
    - tests/test_forget.py
    - engine/search.py

key-decisions:
  - "Exact-path IN (...) placeholders for DB deletion rather than LIKE '%slug%' — avoids Pitfall 5 broad-match deletions"
  - "SpyConnection sqlite3 subclass used in test_fts5_rebuild_after_forget — Python 3.14 made conn.execute read-only, monkey-patching no longer works"
  - "search_notes phrase-quotes all queries via _fts5_query() — FTS5 treats hyphens as subtraction operators in bare queries, causing OperationalError on slug-form names"
  - "sole-reference detection reads file frontmatter (not DB) — file is source of truth per RESEARCH.md guidance"

patterns-established:
  - "Pattern 1: _fts5_query() phrase-quoting — all search_notes callers benefit automatically; no caller changes needed"
  - "Pattern 2: SpyConnection subclass for execute spying — replaces monkey-patch pattern for Python 3.14+"

requirements-completed: [GDPR-01, GDPR-02]

duration: 6min
completed: 2026-03-14
---

# Phase 5 Plan 01: forget_person GDPR Erasure Cascade Summary

**forget_person() implementing GDPR right-to-erasure: person file deletion, sole-reference meeting cascade, backlink cleanup, exact-path DB purge, and mandatory FTS5 shadow-table rebuild**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-14T21:06:13Z
- **Completed:** 2026-03-14T21:12:00Z
- **Tasks:** 2 (TDD RED already committed in 05-00; GREEN implemented here)
- **Files modified:** 3

## Accomplishments

- `forget_person()` fully implemented: deletes person's markdown file, all sole-reference meeting files, removes backlink lines from surviving notes, exact-path DB deletes from notes/relationships/audit_log, explicit FTS5 rebuild (GDPR-02), audit log of the erasure event itself
- `main()` CLI entry point: accepts slug or "First Last" name, normalises to slug, calls forget_person, prints summary
- Fixed `search_notes` FTS5 hyphen-as-subtraction-operator bug via `_fts5_query()` phrase-quoting helper
- All 6 `test_forget.py` tests GREEN; full 103-test suite passes (0 failures)

## Task Commits

1. **TDD GREEN: implement forget_person + fix search phrase-quoting** - `bac5001` (feat)

## Files Created/Modified

- `engine/forget.py` - Full forget_person() + main() CLI entry point
- `tests/test_forget.py` - Removed xfail markers; fixed search arg order; SpyConnection subclass for FTS5 spy
- `engine/search.py` - Added _fts5_query() phrase-quoting helper; applied to both query branches

## Decisions Made

- Used exact-path `IN (...)` for DB deletion (not `LIKE '%slug%'`) per plan's Pitfall 5 guidance — prevents broad-match deletions on short slugs
- `SpyConnection` subclass instead of monkey-patch for `test_fts5_rebuild_after_forget` — Python 3.14 made `sqlite3.Connection.execute` a read-only C-level attribute
- `_fts5_query()` phrase-quoting added to `search_notes` — `alice-smith` was parsed as `alice` minus column `smith`, raising `OperationalError`; phrase quoting is the correct FTS5 idiom for name/slug lookups

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed FTS5 OperationalError on hyphenated slugs in search_notes**
- **Found during:** TDD GREEN (test_search_zero_after_forget)
- **Issue:** `search_notes(conn, "alice-smith")` raised `sqlite3.OperationalError: no such column: smith` — FTS5 parses bare hyphens as subtraction operators
- **Fix:** Added `_fts5_query()` helper that wraps query in FTS5 double-quotes; applied to both query branches in search_notes
- **Files modified:** `engine/search.py`
- **Verification:** `test_search_zero_after_forget` passes; full suite 103 passed
- **Committed in:** bac5001 (task commit)

**2. [Rule 1 - Bug] Fixed test_forget.py search argument order mismatch**
- **Found during:** TDD GREEN (test_search_zero_after_forget)
- **Issue:** Test called `search_notes("alice-smith", conn)` but actual signature is `search_notes(conn, query, ...)`
- **Fix:** Swapped arguments to `search_notes(conn, "alice-smith")`
- **Files modified:** `tests/test_forget.py`
- **Verification:** Test passes after fix
- **Committed in:** bac5001 (task commit)

**3. [Rule 1 - Bug] Fixed FTS5 execute spy using SpyConnection subclass for Python 3.14**
- **Found during:** TDD GREEN (test_fts5_rebuild_after_forget)
- **Issue:** `conn.execute = spy_execute` raised `AttributeError: 'sqlite3.Connection' object attribute 'execute' is read-only` — Python 3.14 made this C-level attribute read-only
- **Fix:** Replaced monkey-patch with `SpyConnection(sqlite3.Connection)` subclass that overrides `execute()` and records SQL; creates fresh `SpyConnection(":memory:")` with `init_schema()`
- **Files modified:** `tests/test_forget.py`
- **Verification:** `test_fts5_rebuild_after_forget` passes
- **Committed in:** bac5001 (task commit)

---

**Total deviations:** 3 auto-fixed (all Rule 1 bugs)
**Impact on plan:** All fixes required for test correctness. No scope creep. search.py fix also improves production correctness for all hyphenated name searches.

## Issues Encountered

- Python 3.14 `sqlite3.Connection.execute` became read-only at C level — resolved via SpyConnection subclass pattern (documented for future tests)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `forget_person()` complete and verified — GDPR-01 and GDPR-02 satisfied
- `engine/search.py` phrase-quoting fix benefits all future plans that search by slug/name
- Ready for plan 05-02 (engine/read.py PII passphrase gate)

---
*Phase: 05-gdpr-and-maintenance*
*Completed: 2026-03-14*
