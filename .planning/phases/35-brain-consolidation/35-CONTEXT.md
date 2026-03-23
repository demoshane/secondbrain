# Phase 35: Brain Consolidation & Knowledge Hygiene — Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Keep the brain coherent as it grows: detect and resolve near-duplicates (merge workflow), enrich stub notes (merge-first, enrich-if-no-match), clean up stale connection graph entries, track health trends over time, and automate consolidation on a daily schedule. All five CONS requirements delivered across three plans.

</domain>

<decisions>
## Implementation Decisions

### A — Merge Workflow (CONS-01)

- **D-01:** Three access surfaces, one shared backend:
  - **MCP tool:** `sb_merge_duplicates` returns candidate pairs; `sb_merge_confirm(pair_id, keep_path, discard_path)` executes the merge with confirm-token pattern.
  - **CLI:** `sb-merge-duplicates` interactive command — prompts through each candidate pair, calls same backend.
  - **GUI:** Merge button in the health panel next to each duplicate pair.
- **D-02:** Merge = copy body/tags/relationships from discard note into keep note (deduplicate), then `sb_forget` discard note (cascade delete from all tables).
- **D-03:** Detection threshold stays at 0.92 (existing). No auto-merge without user confirmation — false positives delete notes.

### B — Stub Enrichment (CONS-02)

- **D-04:** Stub definition: body IS NULL, empty string, or < 50 words.
- **D-05:** Merge-first workflow:
  1. Run stub through duplicate detection (same similarity check as CONS-01).
  2. If similar fuller note found → surface as a merge candidate (route through D-01 merge workflow).
  3. If no match → surface for AI enrichment: suggest content based on title + tags + existing connections (Claude Code pattern, user confirms before save). Same pattern as `sb_capture_smart`.
- **D-06:** `sb_find_stubs` MCP tool returns list of stubs with their similarity matches (if any) so the user can act on them in one session.

### C — Connection Graph Cleanup (CONS-03)

- **D-07:** Scope covers two cases:
  - **Dangling relationships:** Delete `relationships` rows where `source_path` or `target_path` is not in the `notes` table. Safe, always correct.
  - **Bidirectional gaps:** Where A→B exists but B→A doesn't — flag for user review, not auto-create. Some relationships are intentionally one-way (e.g. "mentions").
- **D-08:** Cleanup runs as part of the scheduled consolidation job (CONS-05). Also exposed as `sb_cleanup_connections` MCP tool for on-demand use.
- **D-09:** Report: return counts of deleted dangling rows and flagged bidirectional gaps. Don't silently mutate without surfacing what changed.

### D — Health Trend Tracking (CONS-04)

- **D-10:** New `health_snapshots` DB table (migration in `db.py`):
  ```sql
  CREATE TABLE health_snapshots (
      id INTEGER PRIMARY KEY,
      snapped_at TEXT NOT NULL,
      score INTEGER,
      total_notes INTEGER,
      orphan_count INTEGER,
      broken_count INTEGER,
      duplicate_count INTEGER,
      stub_count INTEGER
  )
  ```
- **D-11:** Snapshot triggered by the scheduled consolidation job (CONS-05). Not triggered on every `sb-health` call — avoids polluting trend with manual runs.
- **D-12:** Retention: 90 days. Cleanup of old snapshots runs with the same scheduled job.
- **D-13:** `sb_health_trend` MCP tool returns snapshots as a time series (last N days). Planner can decide chart/sparkline format for GUI.

### E — Scheduled Consolidation (CONS-05)

- **D-14:** New launchd plist — separate from `sb-watch`. Label: `com.secondbrain.consolidate`.
- **D-15:** Schedule: `StartCalendarInterval` daily at 03:00. macOS launchd fires on next wake if the machine was sleeping — no extra logic needed.
- **D-16:** Consolidation job runs in order:
  1. Archive old action items (existing `archive_old_action_items()`)
  2. Delete dangling relationship rows (D-07)
  3. Take health snapshot (D-10)
  4. Clean up health snapshots older than 90 days (D-12)
- **D-17:** Job does NOT auto-merge or auto-enrich — those require user confirmation. Job only runs safe, idempotent cleanup operations.
- **D-18:** Install via `scripts/install_native.py` alongside existing `sb-api` and `sb-watch` plists.

### Folded Todo

- **T-01:** Add tests for `brain_health.py` — this module is extended significantly in Phase 35; test coverage should ship with each plan that modifies it.

### Claude's Discretion

- GUI health panel layout for merge buttons (extends existing health view)
- Bidirectional gap report format (table vs list vs grouped by note)
- Exact `sb_health_trend` response shape (array of snapshots vs delta-based)
- Similarity threshold for stub-to-merge routing (can start at 0.85, lower than duplicate threshold)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core module
- `engine/brain_health.py` — existing health check functions; all Phase 35 consolidation logic extends this module
- `engine/intelligence.py` — `find_similar()` used by duplicate and stub detection

### Backend integration points
- `engine/db.py` — add `health_snapshots` migration here; follow existing `add_column` / `init_schema` patterns
- `engine/mcp_server.py` — add `sb_merge_duplicates`, `sb_merge_confirm`, `sb_find_stubs`, `sb_cleanup_connections`, `sb_health_trend` tools
- `engine/api.py` — any new REST endpoints for GUI merge/stub flows
- `engine/forget.py` — `forget_note()` cascade delete — used as the discard step in merge

### Frontend
- `frontend/src/components/IntelligencePage.tsx` or equivalent health panel — add merge buttons and trend chart

### Infrastructure
- `scripts/install_native.py` — add `com.secondbrain.consolidate` plist installation here

### Phase context
- `.planning/phases/32-architecture-hardening/32-CONTEXT.md` — FK cascade patterns, relationships table schema
- `.planning/ROADMAP.md` — Phase 35 goal: CONS-01 through CONS-05

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable in Phase 35
- `get_duplicate_candidates(conn, threshold=0.92)` — returns similarity pairs; CONS-01 extends this with merge execution
- `get_empty_notes(conn)` — stub detection foundation; CONS-02 extends with similarity check + enrichment routing
- `archive_old_action_items(conn, days=90)` — already in scheduled path; CONS-05 just calls it
- `forget_note()` in `engine/forget.py` — cascade delete; reuse as the discard step in merge

### Established Patterns
- Confirm-token pattern: `sb_forget`, `sb_anonymize` — use same two-call pattern for `sb_merge_confirm`
- DB migration: add-column functions in `db.py`, called from `init_schema()` — follow for `health_snapshots`
- launchd plists: `scripts/install_native.py` installs sb-api and sb-watch — add consolidate job here

### Integration Points
- `engine/mcp_server.py` — primary consumer surface (MCP-first usage pattern)
- `engine/api.py` — GUI-facing REST endpoints for merge/stub flows
- GUI health panel — extend with merge actions and trend sparkline

</code_context>

<deferred>
## Deferred Ideas

None surfaced — discussion stayed within phase scope.

### Reviewed Todos (not folded)
- **Audit and improve context detection on capture** — capture concern, separate phase
- **Link persons to notes in sidebar** — covered in Phase 34
- **Fix sb_edit wiping YAML frontmatter** — MCP bug, hotfix candidate
- **Fix sb-recap returning nothing despite existing entries** — intelligence bug, separate

</deferred>

---

*Phase: 35-brain-consolidation*
*Context gathered: 2026-03-23*
