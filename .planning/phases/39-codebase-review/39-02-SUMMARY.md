---
phase: 39-codebase-review
plan: "02"
subsystem: architecture-audit
tags: [audit, architecture, dead-code, dual-write, coupling]
dependency_graph:
  requires: []
  provides: [39-findings-architecture.md]
  affects: []
tech_stack:
  added: []
  patterns: []
key_files:
  created:
    - .planning/phases/39-codebase-review/39-findings-architecture.md
  modified: []
decisions:
  - "templates.py confirmed dead — zero engine imports, only referenced by test file"
  - "ratelimit.py confirmed live — imported at module level by watcher.py"
  - "NoteEditor.tsx confirmed live — used as sub-component by NoteViewer.tsx"
  - "Dual-write (tags/people JSON + junction tables) is consistent across all write surfaces"
  - "FK CASCADE gap: action_items and note_embeddings lack CASCADE; only note_tags/note_people have it"
metrics:
  duration: 25
  completed: "2026-03-27"
  tasks: 1
  files: 1
---

# Phase 39 Plan 02: Architecture Audit Summary

Architecture review of 39 Python backend modules, coupling patterns, dead code, dual-write consistency, and api.py structure.

## What Was Done

Systematic read of 20 engine modules, import graph analysis, dual-write path tracing, and dead code verification via grep evidence.

## Key Findings

**13 findings documented** (Critical: 0, High: 1, Medium: 3, Low: 6, Informational: 3)

### High Priority

**ARCH-09: engine/templates.py is dead code**
- `templates.py` has zero imports from any engine module
- Only reference: `tests/test_capture.py:84` — tests a dead module
- Capture writes frontmatter directly; template rendering is unused in production
- Recommendation: delete `engine/templates.py` and the dead test, after confirming no runtime loading

### Medium Priority

**ARCH-05: FK CASCADE missing on action_items and note_embeddings**
- `note_tags` and `note_people` have `ON DELETE CASCADE` (added Phase 32)
- `action_items`, `note_embeddings`, `relationships` do NOT — rely on application-level cascade in `forget.py`
- Gap: direct DELETE FROM notes outside forget_person() path leaves orphan rows
- `get_connection()` correctly enables `PRAGMA foreign_keys = ON`

**ARCH-02: 3 late BRAIN_ROOT re-imports inside api.py function bodies**
- Lines 1194, 1584, 1640 re-import BRAIN_ROOT despite module-level import at line 25
- Likely test isolation workarounds — verify before removing (RESEARCH.md Pitfall 5)

**ARCH-06: api.py at 1754 lines, no Blueprint partitioning**
- 55 Flask routes in one file; 6 natural domain boundaries visible
- Refactor opportunity — not a bug; requires user confirmation before proceeding

### Low / Informational

**ARCH-01:** Duplicate import at api.py:24 (shadowed by line 25) — delete line 24
**ARCH-07:** consolidate.py lazy import comment says "circular import" but that's inaccurate — no circular dependency exists; reason is load-time deferral
**Confirmed live:** rag.py (called from ai.py → capture.py), ratelimit.py (watcher.py), ai.py (CLI + capture)
**Confirmed live:** NoteEditor.tsx (used by NoteViewer.tsx as sub-component)
**Dual-write consistent:** tags and people junction tables are written atomically in all 4 write surfaces (write_note_atomic, update_note, reindex_brain, direct API edit)

## Deviations from Plan

None — plan executed exactly as written. All pre-identified items (A-01 through A-05, D-01 through D-07) were verified.

Correction to RESEARCH.md findings:
- D-04 (ratelimit.py) was pre-identified as "not found imported" — confirmed imported by watcher.py
- D-07 (NoteEditor.tsx) was pre-identified as dead — confirmed live via NoteViewer.tsx import

## Known Stubs

None — this plan produces a findings document, not executable code.

## Self-Check: PASSED

- File `.planning/phases/39-codebase-review/39-findings-architecture.md` exists
- File contains 31 ARCH- references
- Commit `7089181` exists
