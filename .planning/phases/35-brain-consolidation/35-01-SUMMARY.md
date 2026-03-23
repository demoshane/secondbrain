---
phase: 35-brain-consolidation
plan: 01
subsystem: database, api, ui, mcp
tags: [sqlite, fts5, brain-health, merge, mcp, flask, react]

requires:
  - phase: 32-architecture-hardening
    provides: note_tags and note_people junction tables, cascade delete patterns
  - phase: 26-brain-health
    provides: get_duplicate_candidates() in brain_health.py

provides:
  - merge_notes() in engine/brain_health.py — atomic merge with body/tag/relationship consolidation and cascade delete
  - sb_merge_duplicates MCP tool — returns near-duplicate pairs above threshold
  - sb_merge_confirm MCP tool — two-step confirm-token merge execution
  - sb-merge-duplicates CLI command — interactive duplicate review workflow
  - POST /brain-health/merge API endpoint — GUI merge surface
  - GUI Merge button per duplicate pair in IntelligencePage health panel

affects:
  - 35-02 (stale note archival)
  - 35-03 (orphan cleanup)
  - future GUI improvements to health panel

tech-stack:
  added: []
  patterns:
    - "merge_notes() follows ARCH-08 order: DB first (single transaction), then disk file delete, then audit log"
    - "FTS5 rebuild happens outside the main transaction to avoid partial-state rebuilds"
    - "GUI endpoint uses modal confirmation instead of confirm-token (D-03 satisfied by UX layer)"

key-files:
  created:
    - engine/merge_cli.py
    - .planning/phases/35-brain-consolidation/35-01-SUMMARY.md
  modified:
    - engine/brain_health.py
    - engine/mcp_server.py
    - engine/api.py
    - frontend/src/components/IntelligencePage.tsx
    - pyproject.toml
    - tests/test_brain_health.py
    - tests/test_mcp.py

key-decisions:
  - "FTS5 rebuild runs outside the main transaction block to ensure it reads the committed delete state"
  - "test_merge_fts5_rebuilt uses title: column scoped FTS5 query to avoid false positives from merged body content"
  - "GUI endpoint skips confirm-token pattern — window.confirm() modal in frontend satisfies D-03 for this surface"

requirements-completed:
  - CONS-01

duration: 30min
completed: 2026-03-23
---

# Phase 35 Plan 01: Near-Duplicate Merge Workflow Summary

**merge_notes() with body/tag/relationship consolidation, cascade DB delete, FTS5 rebuild, disk unlink — exposed via MCP (confirm-token), CLI (interactive prompts), API (POST /brain-health/merge), and GUI merge button**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-03-23T12:00:00Z
- **Completed:** 2026-03-23T12:28:49Z
- **Tasks:** 2
- **Files modified:** 7 (+ 1 created)

## Accomplishments

- `merge_notes(keep, discard, conn)` atomically merges body (separator-joined), tags (set-union), remaps relationships, cascade-deletes discard from 5 satellite tables, rebuilds FTS5, deletes disk file, writes audit log
- Three access surfaces: `sb_merge_duplicates` + `sb_merge_confirm` (MCP, confirm-token), `sb-merge-duplicates` (CLI, interactive), POST `/brain-health/merge` (API, GUI modal)
- GUI health panel shows Merge button per duplicate pair with `window.confirm()` before POST
- 6 TDD tests for merge_notes + 1 MCP confirm-token test, all green

## Task Commits

1. **Task 1: merge_notes() backend + tests** - `cefb08d` (feat + test, TDD)
2. **Task 2: MCP tools + CLI + API + GUI + MCP test** - `869e926` (feat)

## Files Created/Modified

- `engine/brain_health.py` — added `merge_notes()` with full merge logic and cascade delete
- `engine/mcp_server.py` — added `sb_merge_duplicates` and `sb_merge_confirm` tools
- `engine/merge_cli.py` — new file, `merge_duplicates_main()` interactive CLI
- `engine/api.py` — added `POST /brain-health/merge` endpoint
- `frontend/src/components/IntelligencePage.tsx` — added `handleMerge`, Merge button per duplicate pair
- `pyproject.toml` — added `sb-merge-duplicates` entry point
- `tests/test_brain_health.py` — 6 merge tests (body/tags/rels, cascade, FTS5, disk, audit, ValueError)
- `tests/test_mcp.py` — `test_merge_confirm_requires_token`

## Decisions Made

- FTS5 rebuild runs outside the main `with conn:` transaction block so it reads the committed state of the notes table after the discard note is deleted. Inside the transaction, the content FTS5 table would read uncommitted data.
- `test_merge_fts5_rebuilt` uses `title:"Discard Note"` FTS5 column-scoped query rather than a plain token match, because after merge the keep note's body contains the merged body content (which includes words from the discard note's body).
- GUI `/brain-health/merge` endpoint skips the confirm-token pattern — the `window.confirm()` dialog in the frontend is sufficient user confirmation for the GUI surface (D-03 satisfied at the UX layer, not the API layer).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] FTS5 rebuild placement: moved outside transaction block**
- **Found during:** Task 1 (TDD GREEN phase — test_merge_fts5_rebuilt failed)
- **Issue:** FTS5 `rebuild` inside `with conn:` block reads content table state before transaction commit, leaving stale FTS5 entries
- **Fix:** Moved `conn.execute("INSERT INTO notes_fts(notes_fts) VALUES('rebuild')")` and `conn.commit()` outside the `with conn:` transaction block
- **Files modified:** engine/brain_health.py
- **Verification:** test_merge_fts5_rebuilt passes after fix
- **Committed in:** cefb08d (Task 1 commit)

**2. [Rule 1 - Bug] FTS5 test expectation: scoped to title column**
- **Found during:** Task 1 (TDD GREEN phase — test_merge_fts5_rebuilt still failed after fix 1)
- **Issue:** Plain FTS5 MATCH for "Discard Note" matched the keep note (title="Keep Note" contains "Note", merged body contains "Discard body content." containing "Discard") — false positive
- **Fix:** Changed test to use `title:"Discard Note"` FTS5 column-scoped query, which only matches the title column
- **Files modified:** tests/test_brain_health.py
- **Verification:** test_merge_fts5_rebuilt passes; semantically correct — we want to verify the discard note's title is gone, not that the word "Discard" is absent from all notes
- **Committed in:** cefb08d (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — Bug)
**Impact on plan:** Both fixes required for test correctness. No scope creep.

## Issues Encountered

- Pre-existing failure in `tests/test_intelligence.py::TestConnectionSuggestion::test_check_connections_prints_suggestion` — exists before our changes (verified via git stash). Out of scope per SCOPE BOUNDARY rule.

## Known Stubs

None — all merge functionality is fully wired. No placeholder data flows to UI rendering.

## Next Phase Readiness

- `merge_notes()` is ready for use by Phase 35-02 (stale note archival) and 35-03 (orphan cleanup) if needed
- Frontend rebuild required on host before GUI merge button is visible: `npm run build` in `frontend/` then reinstall uv tool
- Pre-existing test failure in test_intelligence.py should be investigated in a future cleanup pass

---
*Phase: 35-brain-consolidation*
*Completed: 2026-03-23*
