---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: GUI Overhaul & Polish
status: completed
stopped_at: Completed 23-04-PLAN.md
last_updated: "2026-03-16T19:10:56.282Z"
last_activity: 2026-03-16 — Phase 22 complete; note deletion + security hardening + 4 bonus bug fixes
progress:
  total_phases: 8
  completed_phases: 4
  total_plans: 17
  completed_plans: 17
  percent: 99
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-16)

**Core value:** Zero-friction capture that surfaces the right context at the right moment
**Current focus:** Phase 20 — Frontend Bug Fixes (v3.0 start) — COMPLETE

## Current Position

Phase: 23 of 26 (Navigation Polish)
Plan: 0 of 0 — not yet planned
Status: Phase 22 complete; Phase 23 next
Last activity: 2026-03-16 — Phase 22 complete; note deletion + security hardening + 4 bonus bug fixes

Progress: [██████████] 99%

## Performance Metrics

**Velocity:**
- Total plans completed: 1
- Average duration: 3 minutes
- Total execution time: 0.05 hours

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 20 | 01 | 3 min | 2 | 4 |

*Updated after each plan completion*
| Phase 20 P02 | 4 | 2 tasks | 2 files |
| Phase 20 P03 | 15 | 2 tasks | 4 files |
| Phase 21 P01 | 2 | 1 tasks | 2 files |
| Phase 21 P02 | 8 min | 2 tasks | 3 files |
| Phase 21 P03 | 5 min | 1 tasks | 3 files |
| Phase 21 P04 | 0 min | 0 tasks | 0 files | VERIFICATION FAILED |
| Phase 21 P05 | 5 | 2 tasks | 3 files |
| Phase 21 P06 | 5 min | 2 tasks | 1 file |
| Phase 22 P01 | 4 | 2 tasks | 2 files |
| Phase 22 P02 | 12 | 2 tasks | 5 files |
| Phase 22 P03 | 3 | 2 tasks | 3 files |
| Phase 22 P04 | 15 | 3 tasks | 1 files |
| Phase 23 P01 | 6 | 2 tasks | 2 files |
| Phase 23 P02 | 5 | 2 tasks | 2 files |
| Phase 23 P03 | 8 | 2 tasks | 3 files |
| Phase 23 P04 | 25 | 2 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v3.0]: Platform items (encryption, Windows, mobile) deferred to v4.0
- [v3.0 Roadmap]: Use client-side `marked.js` (already vendored) for markdown rendering — no new dep
- [v3.0 Roadmap]: SSE backbone (Phase 21) must ship before any write features (deletion, upload, tags, batch)
- [v3.0 Roadmap]: Extract shared `delete_note()` utility in Phase 22 to prevent cascade miss on GUI delete
- [20-01]: read_note returns body (stripped) by default; ?raw=true returns full content for editor
- [20-01]: save_note parses frontmatter post-write to extract title for SQLite UPDATE
- [Phase 20]: Use LOWER(body) LIKE LOWER(?) for case-insensitive backlinks query
- [Phase 20]: min-height: 0 on flex container is canonical fix for flex child overflow-scroll; apply to entire ancestor chain not just leaf
- [Phase 20]: Vendor marked.min.js — pywebview runs offline, CDN scripts fail silently
- [Phase 21]: _ImmediateTimer helper used in NoteChangeHandler tests to avoid real 300ms debounce wait; documents TDD contract for Path 02 implementor
- [Phase 21]: Queue maxsize=50 with put_nowait + silent pass on Full: slow clients silently dropped rather than blocking broadcast
- [Phase 21]: NoteChangeHandler._is_note() uses Path.parts for files segment check to avoid substring false positives
- [Phase 21]: connectSSE() called at init; matchesCurrent uses endsWith for absolute vs relative path comparison; _sseWasConnected gates reconnect refresh
- [Phase 21]: 500ms suppress window outlasts FSEvents propagation delay after os.replace(); module-level suppression set shared across all NoteChangeHandler instances
- [Phase 21]: easyMDE !== null is the correct primary guard in handleNoteEvent — isDirty alone is stale-prone; any open editor session must be protected regardless of keystroke count
- [Phase 22]: delete_note() stub committed; sb-hook immediately auto-implemented full cascade from 22-02 plan on first commit
- [Phase 22]: relationships table uses rel_type column (not relationship_type); tmp_api_note fixture requires BRAIN_PATH monkeypatch for path resolution
- [Phase 22]: Lazy import of suppress_next_delete inside delete_note() avoids circular import with engine.watcher
- [Phase 22]: _resolve_note_path reads BRAIN_PATH env var; test fixtures must monkeypatch BRAIN_PATH to tmp_path
- [Phase 22]: notes_ad AFTER DELETE trigger handles FTS5 automatically — no explicit rebuild in delete_note()
- [Phase 22 P03]: exitEditMode() called unconditionally in delete confirm handler — named function declaration in ES module, always in scope; typeof guard unnecessary
- [Phase 22]: File deletion working correctly: missing_ok=True on unlink is correct policy — audit_log confirmed deleted notes are gone from disk; user's report was a false alarm (file pre-absent before GUI delete ran)
- [Phase 23]: Tags-only PUT reads+patches frontmatter via python-frontmatter, writes via tempfile+os.replace; targeted DB UPDATE only
- [Phase 23]: Empty query + tags_filter in POST /search bypasses FTS5 (rejects empty queries) and uses direct SELECT with Python-side AND filter
- [Phase 23]: folder-section.collapsed > ul selector hides all child ul elements for both folder and type sections
- [Phase 23]: folderName() uses parts[-2] for top-level folder extraction; falls back to 'other' for flat paths
- [Phase 23]: GET /notes/<path> no tags; use _allNotes cache for chip display
- [Phase 23]: Single-click chip = filter; double-click = inline edit to prevent accidental filter trigger
- [Phase 23]: _suppressNextTagRefresh skips one SSE event after tag save to protect in-progress chip edit
- [Phase 23]: [23-04] Collapse state stored server-side in .sb-gui-prefs.json — localStorage unreliable in pywebview WKWebView
- [Phase 23]: [23-04] POST /notes immediately INSERTs into SQLite; watcher remains as secondary sync
- [Phase 23]: [23-04] Tag autocomplete uses HTML5 datalist — zero deps, native WKWebView support

### Roadmap Evolution

- Phase 27 added: Resolve all open TODOs and Gaps

### Pending Todos

- Fix sb-recap returning nothing despite existing entries (general)
- Fix sb_edit wiping YAML frontmatter (general)
- Link persons to notes in sidebar (ui)
- Audit and improve context detection on capture (general)

### Blockers/Concerns

- [Phase 21 - RESOLVED]: Conflict banner fixed via easyMDE !== null guard in handleNoteEvent (plan 21-06)
- [Phase 21 - RESOLVED]: False-positive "note deleted" on save fixed via suppress_next_delete() in watcher + api (plan 21-05)
- [Phase 21 - ACCEPTED]: Status dot 5s delay — accepted as cosmetic; no code change needed
- [Phase 21]: SSE + pywebview WebKit compatibility not confirmed from official docs — validate with minimal proof-of-concept at phase start
- [Phase 23]: `tags` column existence in `notes` table needs confirmation; if absent, add via `ALTER TABLE ADD COLUMN`
- [Phase 26]: RRF weight calibration is empirical — do not begin without regression fixture set (5 precision + 5 recall queries)

## Session Continuity

Last session: 2026-03-16T19:10:50.838Z
Stopped at: Completed 23-04-PLAN.md
Resume file: None
