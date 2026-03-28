# Phase 42: Add Importance Field to Notes — Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Add an `importance` field to notes: DB column, YAML frontmatter, MCP tools (capture + edit), and GUI (sidebar badges + detail panel dropdown + filter support).

**All four layers in scope:** data model, capture/edit API, GUI display, search filter.
**Out of scope:** ranking/boosting in search scoring (filter-only); no change to default sort order.

</domain>

<decisions>
## Implementation Decisions

### Value Model
- **D-01:** 3-tier categorical enum: `low` / `medium` / `high`
- **D-02:** Default value: `medium` — applied to new notes and existing notes via migration
- **D-03:** DB column: `importance TEXT NOT NULL DEFAULT 'medium'` — follow the existing idempotent `ALTER TABLE ADD COLUMN` migration pattern

### Frontmatter
- **D-04:** Field name: `importance` (matches DB column name)
- **D-05:** Written into YAML frontmatter by `build_post()` in `engine/capture.py`
- **D-06:** All existing notes on disk do NOT need rewriting — `medium` default is sufficient; frontmatter is added at next edit

### Capture & Edit
- **D-07:** `sb_capture` and `sb_capture_batch` — accept optional `importance` param (default: `medium`)
- **D-08:** `sb_capture_smart` — infer importance via keyword heuristics in `engine/typeclassifier.py` (no LLM prompt exists in the smart capture flow; inference must be rule-based to match the existing architecture). Add `classify_importance(text: str) -> str` function: keywords `URGENT`, `CRITICAL`, `important` → `high`; keywords `fyi`, `note to self`, `minor` → `low`; else → `medium`. User can override after capture.
- **D-09:** `sb_edit` — accept optional `importance` param to update the field
- **D-10:** All capture paths write `importance` to both frontmatter and DB column

### GUI Display — Sidebar
- **D-11:** All three importance levels show a badge in the sidebar note list
- **D-12:** Badge labels: `[HIGH]`, `[MED]`, `[LOW]`
- **D-13:** Badge color: use the existing Visily design tokens — high=red/accent, med=yellow/warning, low=grey/muted
- **D-14:** Badge position: before the note title (consistent with the existing `note-type-badge` pattern if applicable, or a new `importance-badge` component)

### GUI Display — Detail Panel
- **D-15:** Importance shown as an inline dropdown in the note detail/right panel metadata section
- **D-16:** Format: `Importance  [High ▾]` — consistent with how `Status` works on project notes
- **D-17:** Changing importance via the dropdown triggers a `PUT /notes/<path>/importance` API call and updates frontmatter on disk

### Search & Filter
- **D-18:** No ranking boost — importance does NOT affect search relevance scores
- **D-19:** Importance is available as a filter param in `sb_search` and the GUI search (filter by `importance=high`)
- **D-20:** `_apply_filters()` in `engine/search.py` extended to support `importance` filter (AND logic with existing filters)
- **D-21:** Default note list sort remains newest-first; "sort by importance (desc)" added as an opt-in sort option in the GUI

### Claude's Discretion
- Exact Tailwind color values for the three badge tiers (match Visily dark palette)
- Whether `importance-badge` reuses the existing `note-type-badge` component or is a new component
- LLM prompt wording for importance inference in `sb_capture_smart`
- API endpoint path: `PUT /notes/<path>/importance` vs patching via existing `sb_edit` route

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing field pattern (DB migration + frontmatter + API)
- `engine/db.py` — all existing `migrate_add_*_column()` functions: copy the idempotent pattern
- `engine/capture.py` — `build_post()` and `capture_note()`: how fields are written to frontmatter and DB
- `engine/api.py` — `PUT /projects/<path>/status` endpoint: copy pattern for importance endpoint

### Existing badge component
- `frontend/src/components/ui/note-type-badge.tsx` — existing badge pattern in the dark design system

### Smart capture classifier
- `engine/classifier.py` — where `sb_capture_smart` LLM prompt lives; extend it for importance inference

### Design system
- `ui-descriptions/UI-DESIGN-BRIEF.md` — Visily dark palette and token reference

### Search filter
- `engine/search.py` — `_apply_filters()` function: extend for importance filter

No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `migrate_add_*_column()` pattern in `engine/db.py`: idempotent `ALTER TABLE ADD COLUMN` with `pass` on duplicate-column error — copy exactly
- `note-type-badge.tsx`: existing dark-styled badge component — likely reusable or a model for `importance-badge`
- `PUT /projects/<path>/status` in `engine/api.py`: inline field-update endpoint pattern to copy for importance
- `_apply_filters()` in `engine/search.py`: AND-logic filter already supports person, tag, note_type, from_date, to_date — add importance here

### Established Patterns
- DB column default: `NOT NULL DEFAULT 'medium'` — no nullable columns for enum fields
- Frontmatter built in `build_post()` in `capture.py`: add `importance` to the 8-field post construction
- MCP tool params: existing tools use optional kwargs with defaults — follow same signature style
- All GUI metadata fields use the dark design system CSS vars; no hardcoded colors

### Integration Points
- `engine/db.py` → add `migrate_add_importance_column()`, call from `init_schema()`
- `engine/capture.py` → `build_post()` + `capture_note()` + `edit_note()`
- `engine/mcp_server.py` → `sb_capture`, `sb_capture_smart`, `sb_edit`
- `engine/api.py` → new `PUT /notes/<path>/importance` endpoint; notes list response to include `importance`
- `engine/search.py` → `_apply_filters()`
- `frontend/src/components/` → sidebar note list (importance badge), RightPanel (importance dropdown)

</code_context>

<specifics>
## Specific Ideas

- Badge labels chosen by user: `[HIGH]`, `[MED]`, `[LOW]` — all three always shown (not hiding medium)
- smart capture inference: "URGENT: prod incident" → high; "random idea about coffee" → low
- GUI dropdown mirrors Status dropdown on project notes — reuse that interaction pattern exactly

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 42-add-importance-field-to-notes*
*Context gathered: 2026-03-28*
