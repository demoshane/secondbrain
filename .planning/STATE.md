---
gsd_state_version: 1.0
milestone: v4.0
milestone_name: Memory & Reliability
status: Phase complete — UAT passed
stopped_at: Completed phase 36 (UAT 2026-03-25)
last_updated: "2026-03-25T12:00:00.000Z"
progress:
  total_phases: 8
  completed_phases: 6
  total_plans: 23
  completed_plans: 23
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-16)

**Core value:** Zero-friction capture that surfaces the right context at the right moment

## Current Position

Phase: 36 (chrome-extension-capture) — COMPLETE
Plan: 4 of 4

## Performance Metrics

**Velocity:** 88 plans completed across 20 phases (v3.0 + v4.0 start). Typical plan: 5–15 min, 2 tasks, 2–5 files.

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|

## Accumulated Context

| Phase 32 P04 | 35 | 2 tasks | 7 files |
| Phase 33 P02 | 20 | 2 tasks | 4 files |
| Phase 33 P01 | 3047 | 2 tasks | 4 files |
| Phase 34 P01 | 150 | 2 tasks | 5 files |
| Phase 34 P02 | 8 | 2 tasks | 4 files |
| Phase 34 P03 | 25 | 2 tasks | 9 files |
| Phase 34 P04 | — | 2 tasks | — | (UATs accepted 2026-03-23)
| Phase 35 P01 | 30 | 2 tasks | 8 files |
| Phase 35 P02 | 15 | 2 tasks | 4 files |
| Phase 35 P03 | 15 | 2 tasks | 9 files |
| Phase 36 P02 | 226 | 2 tasks | 13 files |
| Phase 36 P01 | 176 | 1 tasks | 3 files |
| Phase 36 P03 | 2 | 1 tasks | 3 files |
| Phase 36 P04 | 691 | 2 tasks | 6 files |

### Decisions

Active decisions affecting upcoming work:

- [v3.0]: Platform items (encryption, Windows, mobile) deferred to v4.0
- [Phase 30]: Entity extraction order: extract → merge → build_post(merged) — critical for people write-back
- [Phase 30]: Body-mention fallback removed from note_meta() — people column is single source of truth
- [Phase 30]: sb_person_context uses json_each people column lookup — no body-scan; accepts name or path
- [Phase 31]: sb_capture_smart auto-saves (no confirm_token) — replaces Phase 28-02 stub contract
- [Phase 31]: xfail stubs must patch both engine.paths.BRAIN_ROOT and mcp_mod.BRAIN_ROOT
- [Phase 32]: Export format changed from flat list to {notes, archived_action_items} dict — breaking for sb-export JSON consumers
- [Phase 32]: archive_old_action_items uses executemany+DELETE per row to satisfy semgrep SQL injection scanner
- [Phase 33]: Cooldown resets on both empty-match and successful runs — any path past the cooldown+budget gate counts as a run
- [Phase 33]: Incremental reindex uses utcfromtimestamp(mtime) vs fromisoformat(updated_at) for correct UTC comparison without timezone suffix issues
- [Phase 33]: list_actions and list_people pagination applied in Python (slice after function call) to preserve filter support without dynamic SQL
- [Phase 33]: sb_search total reflects search results up to limit*page, not global COUNT(*) — search engines don't expose unbounded counts
- [Phase 34]: ActionItemList receives people as prop (no internal fetch) — parent owns data, component owns rendering
- [Phase 34]: NoteViewer and RightPanel filter actions client-side by note_path — acceptable for small brain; server-side filter is future optimization
- [Phase 34]: Note navigation in CommandPalette calls setCurrentView('notes') before openNote() to ensure view switch from any page
- [Phase 34]: Toaster mounted in Plan 02 (not Plan 04) so Plan 04 toast calls work immediately
- [Phase 34]: DELETE /people NULLs assignee_path before unlink to prevent orphan action items
- [Phase 34]: sb_create_person MCP tool uses capture_note(note_type='people') — consistent with API pattern
- [Phase 35]: FTS5 rebuild must run outside transaction block — inside transaction it reads pre-commit state, leaving stale entries after content table DELETE
- [Phase 35]: GUI /brain-health/merge skips confirm-token — window.confirm() modal satisfies D-03 at UX layer; MCP surface uses stricter confirm-token pattern
- [Phase 35]: test_get_stub_notes_includes_empty uses empty string not NULL — notes.body has NOT NULL DEFAULT constraint
- [Phase 35]: sb_find_stubs silently catches find_similar exceptions — stubs may have no embeddings, tool must not crash
- [Phase 35]: get_bidirectional_gaps flags gaps for review only, not auto-create — per D-07 design intent
- [Phase 35]: health_snapshots migration is last in init_schema() to avoid ordering issues with other migrations
- [Phase 35]: take_health_snapshot one-per-day guard uses date(snapped_at) = date('now') — strips time component for reliable comparison
- [Phase 35]: consolidate_main imports brain_health lazily inside function body — avoids circular import at module load time
- [Phase 36]: chrome.alarms used for badge polling (not setInterval) — service workers have no persistent timers; alarms permission added to manifest
- [Phase 36]: POST /notes endpoint used in popup (not /smart-capture) — user already selected type in dropdown, so smart classification not needed
- [Phase 36]: source_type added as kwarg to capture_note() — consistent with existing url kwarg pattern; no schema migration needed
- [Phase 36]: create_note() writes url to manual frontmatter string — does not use capture_note(), consistent with that function's existing approach
- [Phase 36]: captureSourceType variable in popup.js tracks source type (gmail/web) for POST body — extend for future source types
- [Phase 36]: Gmail injected button stores pendingCapture in content script (storage accessible from content scripts), relays open-popup-gmail to background — gesture chain not guaranteed, fallback notification used
- [Phase 36]: chrome:// URLs cannot be opened from web pages — install button shows inline instructions only
- [Phase 36]: extensionApiReachable state fetches /ping in useEffect — same check as badge polling but from GUI context

### Pending Todos

- Audit and improve context detection on capture (general)
- [Phase 36 / Chrome extension] Page summarisation feature: summarise the active page via LLM, show summary in extension popup with an "Add to brain" button to save the summary as a note

### Roadmap Evolution

- Phase 37 added: Scale Architecture (100K Notes) — ANN index, incremental reindex, sharding, tiered storage, chunked embeddings, summarization layer, backup & DR

### Blockers/Concerns

None active.

## Session Continuity

Last session: 2026-03-25T07:15:26.462Z
Stopped at: Completed 36-04-PLAN.md
Resume file: None
