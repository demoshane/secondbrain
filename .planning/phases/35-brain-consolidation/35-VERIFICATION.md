---
phase: 35-brain-consolidation
verified: 2026-03-23T19:00:00Z
status: passed
score: 13/13 must-haves verified
re_verification: false
---

# Phase 35: Brain Consolidation Verification Report

**Phase Goal:** Implement brain consolidation — near-duplicate merge workflow, stub enrichment detection, connection graph cleanup, health trend tracking, and scheduled consolidation job.
**Verified:** 2026-03-23T19:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | sb_merge_duplicates MCP tool returns near-duplicate pairs above threshold | VERIFIED | `engine/mcp_server.py:1376` — calls `get_duplicate_candidates(conn, threshold)`, returns `{"pairs": ..., "count": ...}` |
| 2 | sb_merge_confirm requires confirm_token and merges body/tags/relationships into keep note | VERIFIED | `engine/mcp_server.py:1392` — _issue_token() / _consume_token() pattern; calls `merge_notes()` after token consumed |
| 3 | Discard note is cascade-deleted from all tables after merge | VERIFIED | `engine/brain_health.py:156` — merge_notes() deletes from note_embeddings, action_items, note_people, note_tags, relationships, notes; FTS5 rebuilt |
| 4 | GUI health panel shows merge button next to each duplicate pair | VERIFIED | `frontend/src/components/IntelligencePage.tsx:226` — `handleMerge` with `window.confirm()` before POST `/brain-health/merge`; Merge button in duplicate_candidates map |
| 5 | sb-merge-duplicates CLI command prompts user through each candidate pair | VERIFIED | `engine/merge_cli.py:9` — `merge_duplicates_main()` iterates pairs, prompts `[a=keep A, b=keep B, s=skip]`, calls `merge_notes()` |
| 6 | sb_find_stubs MCP tool returns notes with body < 50 words, with similarity matches if any | VERIFIED | `engine/mcp_server.py:1424` — calls `get_stub_notes()` + `find_similar()` per stub; returns `similar_notes` and `action` fields |
| 7 | Stubs with a similar fuller note are routed as merge candidates (not enrichment) | VERIFIED | `engine/mcp_server.py:1454` — `"action": "merge" if matches else "enrich"` |
| 8 | sb_cleanup_connections deletes dangling relationship rows and flags bidirectional gaps | VERIFIED | `engine/mcp_server.py:1462` — calls `delete_dangling_relationships()` and `get_bidirectional_gaps()` |
| 9 | Cleanup report shows counts of deleted dangling rows and flagged gaps | VERIFIED | Returns `{"deleted_dangling": int, "bidirectional_gaps": list, "gap_count": int}` |
| 10 | health_snapshots table created by init_schema migration | VERIFIED | `engine/db.py:423` — `migrate_add_health_snapshots_table()` exists; `engine/db.py:466` — called from `init_schema()` |
| 11 | take_health_snapshot inserts a row with score, counts, and snapped_at date; duplicate-day snapshots are skipped | VERIFIED | `engine/brain_health.py:328` — WHERE date check before insert; returns `{"skipped": True}` if duplicate |
| 12 | sb_health_trend MCP tool returns snapshot time series | VERIFIED | `engine/mcp_server.py:1483` — SELECT from health_snapshots with date range filter, returns `{snapshots, count, days}` |
| 13 | Consolidation job runs: archive actions, delete dangling rels, take snapshot, clean old snapshots | VERIFIED | `engine/consolidate.py:13` — D-16 order: archive_old_action_items → delete_dangling_relationships → take_health_snapshot → cleanup_old_snapshots |

**Score: 13/13 truths verified**

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `engine/brain_health.py` | merge_notes(), get_stub_notes(), delete_dangling_relationships(), get_bidirectional_gaps(), take_health_snapshot(), cleanup_old_snapshots() | VERIFIED | All 6 functions present at lines 156, 268, 288, 305, 328, 355 |
| `engine/merge_cli.py` | merge_duplicates_main() interactive CLI | VERIFIED | File exists; function at line 9 |
| `engine/mcp_server.py` | sb_merge_duplicates, sb_merge_confirm, sb_find_stubs, sb_cleanup_connections, sb_health_trend | VERIFIED | All 5 tools at lines 1376, 1392, 1424, 1462, 1483 |
| `engine/api.py` | POST /brain-health/merge + stub_count in GET /brain-health | VERIFIED | POST endpoint at line 1587; stub_count at line 1570 |
| `engine/consolidate.py` | consolidate_main() entry point | VERIFIED | File exists; function at line 13 with correct D-16 order |
| `engine/db.py` | migrate_add_health_snapshots_table() + init_schema call | VERIFIED | Function at line 423; called from init_schema at line 466 |
| `scripts/install_native.py` | write_consolidate_plist() + main() bootstraps agent | VERIFIED | Function at line 133; main() calls it at line 226 |
| `pyproject.toml` | sb-merge-duplicates + sb-consolidate entry points | VERIFIED | Both at lines 47–48 |
| `frontend/src/components/IntelligencePage.tsx` | Merge button + handleMerge per duplicate pair | VERIFIED | handleMerge at line 85; Merge button at line 228 |
| `tests/test_brain_health.py` | merge tests + stub tests + snapshot tests | VERIFIED | test_merge_copies_body_tags_relationships:329, test_get_stub_notes_word_count:490, test_health_snapshots_migration:613 |
| `tests/test_mcp.py` | test_merge_confirm_requires_token + test_find_stubs_with_matches | VERIFIED | Both present at lines 1260, 1281 |
| `tests/test_consolidate.py` | test_consolidate_main_runs_clean | VERIFIED | Present at line 20 |
| `tests/test_install_native.py` | test_write_consolidate_plist | VERIFIED | Present at line 191 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| engine/mcp_server.py | engine/brain_health.py | import merge_notes | WIRED | Lazy import inside sb_merge_confirm at line 1414 |
| engine/mcp_server.py | engine/brain_health.py | import get_stub_notes | WIRED | Lazy import inside sb_find_stubs at line 1434 |
| engine/mcp_server.py | engine/brain_health.py | import delete_dangling_relationships, get_bidirectional_gaps | WIRED | Lazy import inside sb_cleanup_connections at line 1470 |
| engine/api.py | engine/brain_health.py | import merge_notes for POST endpoint | WIRED | Lazy import at line 1605; GET health imports get_stub_notes at line 1537 |
| engine/merge_cli.py | engine/brain_health.py | import get_duplicate_candidates and merge_notes | WIRED | Both imported inside function body |
| engine/consolidate.py | engine/brain_health.py | import archive_old_action_items, delete_dangling_relationships, take_health_snapshot, cleanup_old_snapshots | WIRED | Lazy import block at line 16 |
| engine/db.py | health_snapshots table | init_schema calls migrate_add_health_snapshots_table | WIRED | Called at line 466 |
| scripts/install_native.py | engine/consolidate.py | plist ProgramArguments references sb-consolidate | WIRED | line 142: `"sb-consolidate"` in ProgramArguments; main() at line 226 |
| frontend IntelligencePage.tsx | POST /brain-health/merge | fetch on Merge button click | WIRED | handleMerge at line 91: `fetch(\`${getAPI()}/brain-health/merge\`)` with keep/discard payload |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| IntelligencePage.tsx (duplicate_candidates) | `health.duplicate_candidates` | GET /brain-health → get_duplicate_candidates() → notes table | Yes — cosine similarity from note_embeddings | FLOWING |
| IntelligencePage.tsx (merge POST) | handleMerge → POST /brain-health/merge | merge_notes() in brain_health.py | Yes — modifies notes, relationships, deletes discard | FLOWING |
| sb_find_stubs (stubs with action) | stubs + similar_notes | get_stub_notes() (DB query) + find_similar() (embeddings) | Yes — real DB queries; graceful fallback when no embeddings | FLOWING |
| sb_health_trend (snapshots) | rows from health_snapshots | SELECT from health_snapshots with date filter | Yes — real DB rows inserted by take_health_snapshot | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| brain_health module exports all 6 functions | `uv run python -c "from engine.brain_health import merge_notes, get_stub_notes, ..."` | "brain_health: OK" | PASS |
| consolidate module importable | `uv run python -c "from engine.consolidate import consolidate_main"` | "consolidate: OK" | PASS |
| merge_cli module importable | `uv run python -c "from engine.merge_cli import merge_duplicates_main"` | "merge_cli: OK" | PASS |
| install_native plist function importable | `uv run python -c "from scripts.install_native import write_consolidate_plist"` | "install_native: OK" | PASS |
| All phase 35 tests pass | `uv run pytest test_brain_health.py test_mcp.py::... test_consolidate.py test_install_native.py::...` | 30 passed, 7 xpassed in 3.69s | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CONS-01 | 35-01 | Near-duplicate merge workflow (merge_notes, MCP tools, CLI, API, GUI) | SATISFIED | merge_notes() + sb_merge_duplicates/confirm + sb-merge-duplicates + POST /brain-health/merge + GUI button — all verified |
| CONS-02 | 35-02 | Stub enrichment detection (get_stub_notes, sb_find_stubs with merge-first routing) | SATISFIED | get_stub_notes() + sb_find_stubs with action=merge/enrich routing — verified |
| CONS-03 | 35-02 | Connection graph cleanup (delete_dangling_relationships, get_bidirectional_gaps, sb_cleanup_connections) | SATISFIED | All three functions + MCP tool — verified |
| CONS-04 | 35-03 | Health trend tracking (health_snapshots table, take_health_snapshot, cleanup_old_snapshots, sb_health_trend) | SATISFIED | DB migration + snapshot functions + MCP tool — verified |
| CONS-05 | 35-03 | Scheduled consolidation job (consolidate_main, launchd plist at 03:00, install_native integration) | SATISFIED | consolidate.py + write_consolidate_plist() + pyproject.toml entry points — verified |

**Note on CONS IDs in REQUIREMENTS.md:** CONS-01 through CONS-05 are defined in plan frontmatter but do not appear in `.planning/REQUIREMENTS.md`. The central requirements file covers only v3.0 milestones (GUIX, GNAV, GUIF, ENGL series). CONS requirements were scoped and tracked entirely within the phase plan files. This is a documentation gap but not a functional gap — all behaviors are implemented and tested.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

Scanned: engine/brain_health.py, engine/consolidate.py, engine/merge_cli.py, engine/mcp_server.py, engine/api.py, engine/db.py, scripts/install_native.py. No TODO/FIXME, no placeholder returns, no empty implementations, no hardcoded stub data flowing to rendering.

---

### Human Verification Required

#### 1. GUI Merge Button — Rendered in Browser

**Test:** Start sb-gui on host, navigate to Intelligence panel, scroll to Health section, confirm Merge button appears next to each duplicate pair
**Expected:** Each duplicate pair row has a "Merge" button; clicking opens a `window.confirm()` dialog; confirming POSTs to /brain-health/merge and refreshes the health data
**Why human:** Requires a running GUI instance; cannot verify frontend rendering programmatically (frontend rebuild also required before the new button is visible)

#### 2. sb-consolidate Launchd Registration

**Test:** On host, run `uv tool install .` then check `launchctl list | grep second-brain` and verify `com.secondbrain.consolidate` is loaded
**Expected:** Agent is registered and shows in launchctl list; plist file present in ~/Library/LaunchAgents/
**Why human:** Requires running `scripts/install_native.py` as part of the full install pipeline; cannot verify launchd state programmatically without running the installer

---

### Gaps Summary

No gaps. All 13 observable truths verified. All artifacts exist, are substantive, and are correctly wired. Tests pass. The only items requiring human verification are UI rendering (GUI Merge button) and launchd registration state — both are standard install/runtime concerns, not implementation gaps.

---

_Verified: 2026-03-23T19:00:00Z_
_Verifier: Claude (gsd-verifier)_
