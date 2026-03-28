---
gsd_state_version: 1.0
milestone: v4.0
milestone_name: Memory & Reliability
status: Ready to execute
stopped_at: Completed 41.3-07-PLAN.md — Chrome extension page summarisation
last_updated: "2026-03-28T16:20:10.093Z"
progress:
  total_phases: 18
  completed_phases: 12
  total_plans: 82
  completed_plans: 80
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-16)

**Core value:** Zero-friction capture that surfaces the right context at the right moment

## Current Position

Phase: 41.3 (ui-polish) — EXECUTING
Plan: 8 of 8

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
| Phase 38 P01 | 601 | 2 tasks | 4 files |
| Phase 38 P02 | 25 | 2 tasks | 6 files |
| Phase 38 P03 | 480 | 2 tasks | 4 files |
| Phase 38 P04 | 459 | 2 tasks | 4 files |
| Phase 38 P06 | 25 | 2 tasks | 7 files |
| Phase 38 P05 | 10 | 2 tasks | 2 files |
| Phase 39 P04 | 15 | 1 tasks | 1 files |
| Phase 39 P03 | 420 | 1 tasks | 1 files |
| Phase 39 P02 | 25 | 1 tasks | 1 files |
| Phase 39 P05 | 900 | 1 tasks | 1 files |
| Phase 39 P01 | 179 | 1 tasks | 1 files |
| Phase 39 P06 | 180 | 1 tasks | 1 files |
| Phase 39 P08 | 30 | 2 tasks | 4 files |
| Phase 39 P12 | 15 | 2 tasks | 1 files |
| Phase 41 P01 | 193 | 3 tasks | 17 files |
| Phase 41 P02 | 96 | 2 tasks | 4 files |
| Phase 41 P04 | 203 | 2 tasks | 4 files |
| Phase 41 P05 | 233 | 2 tasks | 4 files |
| Phase 41 P03 | 3 | 3 tasks | 4 files |
| Phase 41.1-visual-fidelity P01 | 83 | 2 tasks | 2 files |
| Phase 41.1 P04 | 96 | 2 tasks | 3 files |
| Phase 41.1 P03 | 115 | 2 tasks | 1 files |
| Phase 41.1 P02 | 691 | 2 tasks | 2 files |
| Phase 41.2 P01 | 5 | 1 tasks | 1 files |
| Phase 41.2-interactive-gaps P05 | 525638 | 1 tasks | 1 files |
| Phase 41.2 P02 | 8 | 1 tasks | 1 files |
| Phase 41.2 P04 | 5 | 1 tasks | 1 files |
| Phase 41.2-interactive-gaps P03 | 5 | 1 tasks | 1 files |
| Phase 41.2 P06 | 1 | 2 tasks | 3 files |
| Phase 41.3 P01 | 5 | 1 tasks | 1 files |
| Phase 41.3 P02 | 65 | 1 tasks | 2 files |
| Phase 41.3 P03 | 98 | 3 tasks | 3 files |
| Phase 41.3 P04 | 300 | 1 tasks | 4 files |
| Phase 41.3 P05 | 600 | 3 tasks | 2 files |
| Phase 41.3 P06 | 12 | 1 tasks | 7 files |
| Phase 41.3 P07 | 3 | 2 tasks | 4 files |

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
- [Phase 38]: hnswlib compiled from source on macOS 26 using SDKROOT+CXXFLAGS for MacOSX15.4.sdk
- [Phase 38]: load_or_build_index returns None (not raises) when no file and no conn — caller handles fallback to sqlite-vec
- [Phase 38]: archive_old_audit_entries uses executemany+DELETE per row — mirrors Phase 32 pattern for semgrep compliance
- [Phase 38]: shard_note disables PRAGMA foreign_keys during transaction — SQLite has no deferred FK support for UPDATE; child tables (note_tags, note_people) have FK on notes.path
- [Phase 38]: Fernet key stored at ~/.config/second-brain/backup.key (chmod 600) — outside brain folder, not in Drive sync or backup archive
- [Phase 38]: restore_main uses two-step confirm_token (secrets.token_hex(8), 60s expiry) — mirrors MCP destructive op pattern
- [Phase 38]: CHUNK_THRESHOLD < CHUNK_SIZE: short notes (<600 chars) reuse note-level blob as single chunk rather than re-embedding
- [Phase 38]: conftest stub_engine_embeddings skip list extended with TestSplitTextIntoChunks, TestEmbedChunks, TestNoteChunksSchema — new chunking test classes need real embeddings module
- [Phase 38]: summarize_note uses _router.get_adapter('public') — consistent with recap_entity pattern, not direct call_claude
- [Phase 38]: SUMMARY_THRESHOLD=2000 chars, SUMMARY_MAX_INPUT=8000 chars — balance coverage vs token cost
- [Phase 38]: search_semantic uses ANN-first pattern: hnswlib knn_query tried first, any exception falls back to sqlite-vec
- [Phase 38]: _enrich_with_excerpts skips dimension-mismatched chunks (len check) to handle 384-dim test stubs vs 768-dim production vectors
- [Phase 38]: excerpt enrichment called at search_hybrid merge point, not inside sub-search functions, to avoid double-enrichment
- [Phase 39]: MCP tool coverage matrix: 13/22 tools tested; sb_anonymize, sb_capture_link, sb_actions_done, sb_connections, sb_digest are highest-priority gaps
- [Phase 39]: PERF-01: note_meta backlink detection should use relationships table, not LIKE scan on body
- [Phase 39]: PERF-07: get_duplicate_candidates is O(n^2); replace with ANN-based approach from consolidate.py
- [Phase 39]: PERF-08: recap_entity bypasses Phase 32 junction tables — oversight, fix in remediation
- [Phase 39]: Missing indexes: notes(archived) and action_items(note_path) highest priority additions
- [Phase 39]: templates.py confirmed dead — zero engine imports; delete candidate
- [Phase 39]: FK CASCADE gap: action_items and note_embeddings lack ON DELETE CASCADE (only note_tags/note_people have it from Phase 32)
- [Phase 39]: Dual-write (tags/people JSON + junction tables) verified consistent across all 4 write surfaces in capture.py, reindex.py, api.py
- [Phase 39]: templates.py confirmed dead — zero engine callers, only isolated test import
- [Phase 39]: NoteEditor.tsx alive — reachable via App.tsx → NoteViewer.tsx → NoteEditor.tsx
- [Phase 39]: sharding.py implemented but unwired from any user-facing CLI or API surface
- [Phase 39]: SEC-01 High: 8 unguarded int() calls in api.py cause HTTP 500 on bad input — fix in remediation plans
- [Phase 39]: SEC-04 Medium: sb_files subfolder param allows path traversal outside files_dir — needs resolve+is_relative_to guard
- [Phase 39]: Security: no SQL injection found in full codebase audit — all queries use parameterized placeholders
- [Phase 39]: 39-FINDINGS.md: 31 consolidated findings (0 Critical, 6 High, 11 Medium, 14 Low) — 6 remediation groups planned for Wave 3
- [Phase 39]: _int_param uses abort(400) — consistent with Flask error handling; min/max clamping preserves existing behaviour while adding bad-input rejection
- [Phase 39]: sb_files subfolder traversal guard uses resolve()+is_relative_to() pattern — resolves symlinks before comparison to prevent bypass
- [Phase 39]: sb_anonymize scrub check uses frontmatter.load() to parse past YAML; sb_actions_done idempotent: SQLite UPDATE rowcount=1 even on already-done row
- [Phase 41]: prose-invert always applied (not dark:prose-invert) since app is always dark — dark conditionals are dead code
- [Phase 41]: noteTypeColorMap exported from badge.tsx so downstream components can import without re-declaring the hex pairs
- [Phase 41]: Search mode selector hidden behind SlidersHorizontal toggle (showAdvanced state, default false)
- [Phase 41]: Inline Upload/Delete action bar removed from App.tsx — plan 03 re-adds delete inside NoteViewer
- [Phase 41]: ProjectsPage uses inline select form for Link Meeting (not modal) — simpler UX, avoids extra dialog layer
- [Phase 41]: link_meeting_to_project stores meeting_sp (resolved path) directly — consistent with existing route patterns in api.py
- [Phase 41]: ActionsPage uses button-group filter (Open/Done/All) instead of Select dropdown per UI-SPEC interaction pattern
- [Phase 41]: IntelligencePage Chrome Extension section removed — two-column layout has no place for one-time setup panel
- [Phase 41]: LinksPage adds delete capability and markdown body rendering — gaps flagged in ui-descriptions
- [Phase 41]: NoteViewer delete uses direct fetch DELETE + loadNotes() refresh — context.deleteNote does not exist
- [Phase 41]: NoteEditor replaces MDEditor with plain textarea — matches Visily mockup
- [Phase 41]: RightPanel collapse persisted to localStorage 'rp-collapsed' key — survives page refresh
- [Phase 41.1]: HealthScoreGauge uses hex color values (#22c55e, #fbbf24, #ef4444) for SVG stroke — Tailwind class names don't apply to SVG attributes
- [Phase 41.1]: Sidebar groupByFolderThenType extracts folder from first path segment (indexOf('/') == -1 -> 'other'); FOLDER_ORDER drives sort
- [Phase 41.1]: AvatarInitials inlined in PeoplePage — single consumer, extract later if needed by other pages
- [Phase 41.1]: ProjectsPage stat tiles placed inside header block with mt-4 — tiles feel attached to header
- [Phase 41.1]: Priority Actions urgency computed client-side: overdue=High(red), <=7d=Med(amber), >7d=Low(green)
- [Phase 41.1]: Quick Capture on IntelligencePage POSTs to /capture with note_type:note — same contract as other capture paths
- [Phase 41.1]: ActionsPage per-group collapse uses Map<string, boolean> with allCollapsed as fallback default
- [Phase 41.1]: MeetingsPage date chip uses formatDateChip() helper returning {month, day} with MONTH_ABBR lookup
- [Phase 41.2]: Tags fetched via separate GET /notes/${enc} — meta endpoint does not expose tags directly; detailPeople sourced from meta.people already fetched in loadProjectDetail
- [Phase 41.2]: Preview toggle in NoteEditor is a ghost button above body — no toolbar or split-view; ReactMarkdown reused from existing deps
- [Phase 41.2]: MeetingsPage participants mapped from {name,path} objects to name strings at fetch boundary — type declaration stays string[], normalization at fetch time
- [Phase 41.2]: PeoplePage Link Note uses Link icon (not Plus) to distinguish linking existing notes from new creation
- [Phase 41.2]: link_meeting_to_project: two-pass DB lookup pattern — try store_path(relative) first, fall back to raw meeting_path for pre-Phase-32 absolute-path rows; row_factory=sqlite3.Row added for diagnostic type access
- [Phase 41.2]: title_and_body_title / title_and_body_body key names chosen to avoid collision with existing single-field branches
- [Phase 41.2]: NoteEditor saveNote sends {body} not {content} when title absent — body-only branch preserves frontmatter
- [Phase 41.3]: Sidebar single-level type grouping: remove FOLDER_ORDER, replace groupByFolderThenType with groupByType returning flat Map<string, Note[]>
- [Phase 41.3]: Select appearance:none + SVG data-URI chevron chosen over OS-default styling for native-dark look in Chrome extension popup
- [Phase 41.3]: ActionItemRow 'Set deadline' ghost uses group-hover visibility — only shown on row hover to avoid clutter
- [Phase 41.3]: ProjectsPage Notes section added (body was missing from detail panel entirely) — Notes CollapsibleSection now shows/edits body, Related Notes section kept for backlinks
- [Phase 41.3]: Inline edit uses PUT /notes/{path} with {body:...} — body-only branch already in api.py, no PATCH route needed
- [Phase 41.3]: meta endpoint omits unresolved plain-text people entries (path: None) — noise from old entity extraction
- [Phase 41.3]: Tags section always visible in RightPanel when note is open — discoverable even when empty
- [Phase 41.3]: AttachmentsSection always visible (no length > 0 gate) — discoverable even when empty
- [Phase 41.3]: FileUploadModal.notePath prop overrides NoteContext.currentPath — required for entity pages where selected path != NoteContext currentPath
- [Phase 41.3]: POST /summarise-url placed at top level (not /intelligence/*) — it is extension-facing, not GUI-facing
- [Phase 41.3]: _router.get_adapter('public') used for /summarise-url — consistent with summarize_note() and recap_entity() patterns
- [Phase 41.3]: Extension summarise button event handlers attached unconditionally before URL-param early-return — fixes handler gap in Gmail popup path

### Pending Todos

- Audit and improve context detection on capture (general)
- [Phase 36 / Chrome extension] Page summarisation feature: summarise the active page via LLM, show summary in extension popup with an "Add to brain" button to save the summary as a note
- [Phase 39 / Codebase Review] F-18 SEC-06: CORS accepts any chrome-extension://* origin — accepted risk, document explicitly (engine/api.py:64)
- [Phase 39 / Codebase Review] F-19 SEC-07: Host header injection in /ui script tag — localhost-only, accepted risk (engine/api.py:786-791)
- [Phase 39 / Codebase Review] F-20 SEC-08: /ui/prefs PUT has no size/schema validation — localhost-only, low impact (engine/api.py:783)
- [Phase 39 / Codebase Review] F-21 SEC-09: Chrome extension <all_urls> permission scope — accepted risk, on-demand only (manifest.json:21)
- [Phase 39 / Codebase Review] F-22 ARCH-06: api.py at 1754 lines with no Flask Blueprint partitioning — defer to dedicated refactor plan (engine/api.py)
- [Phase 39 / Codebase Review] F-23 ARCH-07: consolidate.py lazy import comment says "circular import" but reason is load-time deferral — clarify comment (engine/consolidate.py:99-108)
- [Phase 39 / Codebase Review] F-24 PERF-09: list_people fetches all records then paginates in Python — known Phase 33 trade-off (engine/api.py:317-331)
- [Phase 39 / Codebase Review] F-25 PERF-10: get_stale_notes fetches 3× limit then filters in Python — acceptable at current scale (engine/intelligence.py:241-283)
- [Phase 39 / Codebase Review] F-26 PERF-11: startup() uses glob.glob for disk count instead of DB COUNT(*) (engine/api.py:1731)
- [Phase 39 / Codebase Review] F-27 DEAD-03: Deprecated /people route aliases still live; IntelligencePage.tsx:50 not yet migrated to /persons (engine/api.py:318,456,543,574)
- [Phase 39 / Codebase Review] F-28 DEAD-04: os.environ.get("BRAIN_PATH") repeated 13× in api.py instead of using imported BRAIN_ROOT (engine/api.py)
- [Phase 39 / Codebase Review] F-29 DEAD-05: json.loads(col or "[]") pattern repeated 13× across 5 files — no shared helper (multiple engine modules)
- [Phase 39 / Codebase Review] F-30 DEAD-07: ensure_person_profile() writes to person/ (singular) but brain uses people/ (plural) — needs Phase 30/32 audit before changing (engine/links.py:46-60)
- [Phase 39 / Codebase Review] F-31 DEAD-08: datetime.utcnow() used 33× across 13 files — deprecated in Python 3.12+ (multiple engine modules)

### Roadmap Evolution

- Phase 37 added: Scale Architecture (100K Notes) — ANN index, incremental reindex, sharding, tiered storage, chunked embeddings, summarization layer, backup & DR
- Phase 42 added: Add importance field to notes — optional 250-char field capturing why a note matters, across DB, capture paths, MCP tools, Chrome plugin, and GUI
- Phase 44 added: Backend code cleanup — F-22 (api.py Blueprint partitioning), F-27 (deprecated /people aliases), F-28 (BRAIN_PATH consolidation), F-29 (json.loads helper), F-30 (ensure_person_profile wrong path), F-31 (datetime.utcnow() → datetime.now(UTC))

### Blockers/Concerns

None active.

## Session Continuity

Last session: 2026-03-28T16:20:10.082Z
Stopped at: Completed 41.3-07-PLAN.md — Chrome extension page summarisation
Resume file: None

### Next action

Plan phase 41 (visual-redesign).
