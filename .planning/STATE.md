---
gsd_state_version: 1.0
milestone: v4.0
milestone_name: Memory & Reliability
status: Ready to execute
stopped_at: Completed 35-01-PLAN.md
last_updated: "2026-03-23T12:30:21.079Z"
progress:
  total_phases: 8
  completed_phases: 3
  total_plans: 20
  completed_plans: 16
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-16)

**Core value:** Zero-friction capture that surfaces the right context at the right moment

## Current Position

Phase: 35 (brain-consolidation) — EXECUTING
Plan: 2 of 3

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

### Pending Todos

- Audit and improve context detection on capture (general)

### Roadmap Evolution

- Phase 37 added: Scale Architecture (100K Notes) — ANN index, incremental reindex, sharding, tiered storage, chunked embeddings, summarization layer, backup & DR

### Blockers/Concerns

None active.

## Session Continuity

Last session: 2026-03-23T12:30:21.073Z
Stopped at: Completed 35-01-PLAN.md
Resume file: None
