# Phase 37: Housekeeping — Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Close known UX gaps and test coverage holes surfaced during v4.0 development. Eight targeted fixes:
1. Fix broken `sb_recap` MCP weekly view (routes to entity recap, not session recap)
2. Action item creation from person note view
3. People chips in NoteViewer — add/remove person links on a note
4. Cascade delete completeness — pre-delete impact preview + orphan cleanup
5. Tests for `install_subagent.py`
6. Fix 3 failing Playwright tests (title sync, delete flow, people badge)
7. Fix 4 failing embedding reindex tests (race condition with background thread)
8. Drive sync setup guidance in setup.sh + sb-health Drive check

Drive setup (37-08) is a hard prerequisite for Phase 38 backup — must not be skipped.

</domain>

<decisions>
## Implementation Decisions

### 37-01: sb_recap weekly view fix
- `sb_recap` MCP tool currently calls `recap_entity()` when `name=None`, returning "No recap available"
- Fix: when `name=None`, call `generate_recap_on_demand()` instead — already exists in `intelligence.py`
- No MCP signature change needed

### 37-02: Action item creation from person note view
- ActionItemList component already renders in PeoplePage detail view
- Add a create button/inline form consistent with the existing ActionItemList creation pattern (Phase 34)

### 37-03: People chips in NoteViewer
- **Location:** NoteViewer (middle panel) — same location as tag chips/TagAutocomplete
- **Pattern:** People chips alongside tag chips. `+` opens autocomplete dropdown sourced from `/persons` endpoint. `×` removes the link.
- **Writes to:** `note_people` junction table + `people` JSON column on the note
- **Read from:** `note_people` junction table (already populated by entity extraction on capture)
- Same visual and interaction pattern as existing tag editing — no new UI paradigm

### 37-04: Cascade delete — impact preview + orphan cleanup
- **Pre-delete impact summary:** Before executing any delete, query and return counts:
  `{ action_items: N, relationships: N, appears_in_people_of: N_notes }`
  Show this in the GUI delete confirmation modal AND in `sb_forget` pre-confirmation step (two-step token response)
- **`delete_note()` gaps to fix:**
  - Add `DELETE FROM note_people WHERE person = ?` when deleting a person note (other notes' people links become orphaned — currently not cleaned)
  - Add `UPDATE/NULL action_items WHERE assignee_path = ?` when deleting a person note (assignee references orphaned)
- **`forget_person()` gap to fix:**
  - Add `UPDATE/NULL action_items WHERE assignee_path IN (person_paths)` — currently missing
- **All other cascade targets already handled** (FK ON DELETE CASCADE active for note_tags + note_people on note_path; relationships cleaned both directions; note_embeddings, audit_log cleaned)
- Impact preview is informational, not a hard blocker — user still confirms and deletes

### 37-07: Embedding reindex test fix
- Tests fail due to race condition: embeddings run in a background thread, test asserts immediately after
- **Fix:** Add `synchronous=True` parameter to the embed pass function (or reindex call) — runs embedding inline, no thread, blocks until done
- `synchronous=True` used in tests only; production keeps non-blocking behavior
- Ollama IS running with `nomic-embed-text:latest` — no mock needed, tests should hit real embeddings

### 37-08: Drive sync setup
- **User has added `~/SecondBrain` to Google Drive Desktop mirror sync (done 2026-03-25)**
- Drive Desktop skips hidden folders (`.meta/`) automatically — SQLite DB and embeddings stay local-only as intended
- **setup.sh guidance:** Detect if `/Applications/Google Drive.app` exists. If not installed, print step-by-step instructions. If installed, print reminder to confirm `~/SecondBrain` is added in Drive Preferences → My Computer.
- **sb-health Drive check (3-tier):**
  - ✅ Drive installed + process running + DriveFS account DB present (`~/Library/Application Support/Google/DriveFS/{account_id}/mirror_sqlite.db`)
  - ⚠️ Drive installed but process not running — warn "Drive not running, brain won't sync"
  - ⚠️ Drive not installed — warn with setup instructions
  - ℹ️ Always append: "Confirm ~/SecondBrain is added in Drive preferences"
- Detection via: `pgrep -x "Google Drive"`, presence of `/Applications/Google Drive.app`, glob for `mirror_sqlite.db` in DriveFS account dir
- Drive check is a warning, not a hard error — brain is fully functional without Drive

### Claude's Discretion
- Action item creation UX in person view (inline vs modal) — follow whatever pattern ActionItemList already uses for creation
- Exact wording of Drive setup instructions in setup.sh
- Whether assignee_path is NULLed or the action item is deleted when a person is removed (NULL preferred — preserve the action item)
- Playwright test fixes (37-06) — pure debugging, no design decisions

</decisions>

<specifics>
## Specific Ideas

- Drive xattr on `~/SecondBrain` has no Drive-specific markers — detection must use process check + DriveFS DB presence, not xattr
- The `mirror_sqlite.db` lives at `~/Library/Application Support/Google/DriveFS/{account_id}/mirror_sqlite.db`; glob for it (account_id is a numeric string)
- `generate_recap_on_demand()` already accepts `window_days` param — wiring the MCP tool to pass `--days` is optional (Claude's discretion)

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs or ADRs for this phase — all requirements captured in decisions above.

### Key source files to read before planning
- `engine/intelligence.py` — `generate_recap_on_demand()`, `recap_entity()`, `sb_recap` wiring
- `engine/mcp_server.py` — `sb_recap` tool definition (lines ~570–600), `sb_forget` two-step flow
- `engine/delete.py` — `delete_note()` full cascade logic
- `engine/forget.py` — `forget_person()` full GDPR erasure logic
- `engine/db.py` — `action_items` schema (assignee_path column), `note_people` schema (FK cascade)
- `engine/embeddings.py` — `embed_texts()`, background thread dispatch
- `engine/reindex.py` — `embed_pass()`, incremental reindex
- `frontend/src/components/NoteViewer.tsx` — tag chip + TagAutocomplete pattern to replicate for people
- `frontend/src/components/PeoplePage.tsx` — person detail view, ActionItemList usage
- `setup.sh` — existing structure to extend with Drive guidance
- `engine/brain_health.py` — `get_brain_health_report()` to extend with Drive check
- `scripts/install_subagent.py` — 20-line script to write tests for
- `tests/test_embeddings.py` — `TestReindexGeneratesEmbeddings` failing tests

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `TagAutocomplete` component + tag chip pattern in `NoteViewer.tsx` — replicate exactly for people chips
- `ActionItemList` component — already used in PeoplePage, has creation affordance to extend
- `generate_recap_on_demand(conn, window_days)` in `intelligence.py` — ready to wire into MCP
- `get_brain_health_report()` in `brain_health.py` — extend with Drive check section

### Established Patterns
- Two-step token confirmation for destructive MCP ops — `sb_forget` already has this; add impact counts to the first-step response
- GUI delete confirmation modal (`DeleteNoteModal.tsx`) — add impact summary display before confirm button
- FK `ON DELETE CASCADE` is active (`PRAGMA foreign_keys = ON` in `get_connection()`) — covers note_tags and note_people own rows automatically
- Background thread pattern in `capture_note()` — add `synchronous` flag to bypass for tests

### Integration Points
- People chips → `GET /persons` for autocomplete, `PATCH /notes/{path}` (or new endpoint) to update people field
- Drive health check → new section in `get_brain_health_report()` return dict, surfaced in `sb-health` CLI and Intelligence page

</code_context>

<deferred>
## Deferred Ideas

- None raised — discussion stayed within phase scope

</deferred>

---

*Phase: 37-housekeeping*
*Context gathered: 2026-03-25*
