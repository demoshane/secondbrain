---
phase: 27-search-quality-tuning
plan: 03
subsystem: capture, intelligence, mcp
tags: [sqlite, upsert, frontmatter, recap, heuristics, tdd]

requires:
  - phase: 27-01
    provides: xfail test stubs for sb_edit frontmatter and recap fixes

provides:
  - write_note_atomic with update=True parameter using INSERT OR REPLACE
  - sb_edit passes update=True so frontmatter is preserved on edit
  - recap_main() fallback to 5 most-recent notes when git-context yields 0 rows
  - _suggest_note_type_from_title() heuristic for meeting/people type detection

affects:
  - mcp_server (sb_edit no longer wipes frontmatter)
  - intelligence (recap now returns content even with no context match)
  - capture CLI (type suggestion available for interactive use)

tech-stack:
  added: []
  patterns:
    - "INSERT OR REPLACE (UPSERT) gated by update=True param — default False preserves backward compat"
    - "Recap fallback: context query 0 rows -> SELECT 5 most-recent by updated_at"
    - "Title heuristics: keyword set for meeting, regex for Firstname Lastname people"

key-files:
  created: []
  modified:
    - engine/capture.py
    - engine/mcp_server.py
    - engine/intelligence.py
    - tests/test_mcp.py
    - tests/test_intelligence.py

key-decisions:
  - "write_note_atomic update=True uses INSERT OR REPLACE; False (default) keeps INSERT for all existing callers"
  - "sb_edit passes update=True — the only caller that needs upsert semantics"
  - "recap fallback prints list (not AI summary) — avoids adapter call when context is missing"
  - "_suggest_note_type_from_title() is a pure helper, never called automatically — ready for interactive CLI use"
  - "Test fix: monkeypatch DB_PATH as Path obj (not str); patch BRAIN_ROOT in mcp_mod; use absolute note path in sb_edit call"

patterns-established:
  - "UPSERT pattern: add update=False param, branch on sql_verb, log 'update' vs 'create' in audit"

requirements-completed:
  - ENGL-02

duration: 22min
completed: 2026-03-17
---

# Phase 27 Plan 03: Bug Fix Trio Summary

**INSERT OR REPLACE upsert for sb_edit frontmatter preservation, recap fallback to recent notes, and title-based type-suggestion heuristics**

## Performance

- **Duration:** 22 min
- **Started:** 2026-03-17T17:55:24Z
- **Completed:** 2026-03-17T18:17:07Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- `sb_edit` no longer wipes YAML frontmatter: `write_note_atomic` now accepts `update=True` which uses `INSERT OR REPLACE` instead of bare `INSERT`, avoiding UNIQUE constraint error on existing notes
- `recap_main()` returns useful output even when git-context search finds no matching notes: falls back to listing 5 most-recent notes with type and date
- `_suggest_note_type_from_title()` added to capture pipeline: returns `"meeting"` for standup/retro/sync/review keyword titles, `"people"` for Firstname-Lastname pattern, `None` otherwise

## Task Commits

1. **Task 1: Fix sb_edit frontmatter wipe** - `822879d` (feat — bundled with 27-02 commit due to pre-commit stash/restore behaviour)
2. **Task 1 test RED** - `d9ae430` (test — xfail stubs for recap fallback + heuristics)
3. **Task 2: Fix recap fallback + capture heuristics** - `3bfcaee` (feat)

## Files Created/Modified

- `engine/capture.py` - Added `update: bool = False` to `write_note_atomic()`; `INSERT OR REPLACE` when True; added `_suggest_note_type_from_title()` helper
- `engine/mcp_server.py` - `sb_edit` passes `update=True` to `write_note_atomic`
- `engine/intelligence.py` - `recap_main()` fallback: when 0 rows from context query, prints 5 most-recent notes
- `tests/test_mcp.py` - Promoted `test_sb_edit_preserves_frontmatter` from xfail; fixed test isolation (DB_PATH as Path, BRAIN_ROOT patch, absolute path)
- `tests/test_intelligence.py` - Added and promoted 4 tests for recap fallback and type heuristics

## Decisions Made

- `update=True` param defaults to `False` so all existing callers (capture_note, etc.) are unaffected — only `sb_edit` opts in
- Recap fallback prints a plain list rather than invoking the AI adapter — faster, no adapter dependency for fallback path
- `_suggest_note_type_from_title()` is a standalone helper (not wired into CLI yet) — ready for Phase 27+ interactive capture prompt work

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test isolation fix for test_sb_edit_preserves_frontmatter**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Test used relative path `"ideas/test-note.md"` which resolves to CWD, not tmp brain; `DB_PATH` monkeypatched as str but `get_connection()` expects `Path`; `BRAIN_ROOT` not patched in `mcp_mod`
- **Fix:** Changed monkeypatch to use `Path` object for `DB_PATH`; added `monkeypatch.setattr(mcp_mod, "BRAIN_ROOT", brain)`; changed `sb_edit` call to use absolute `str(note_path)`
- **Files modified:** `tests/test_mcp.py`
- **Verification:** `test_sb_edit_preserves_frontmatter` passes
- **Committed in:** `822879d` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — test bug)
**Impact on plan:** Test isolation fix was necessary to make the promoted test pass. No scope creep.

## Issues Encountered

- Pre-commit hook stashes unstaged files before running, which caused the first commit attempt to report "no changes added" even though staged files were present. The commit DID go through (verified via `git show`) — the message was misleading.

## Next Phase Readiness

- `sb_edit` is now safe for all frontmatter-bearing notes
- `recap_main()` always returns useful output
- `_suggest_note_type_from_title()` available for wiring into CLI interactive prompts in a future plan

---
*Phase: 27-search-quality-tuning*
*Completed: 2026-03-17*
