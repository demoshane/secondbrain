---
phase: 34
reviewers: [claude]
reviewed_at: 2026-03-22T00:00:00Z
plans_reviewed:
  - 34-01-PLAN.md
  - 34-02-PLAN.md
  - 34-03-PLAN.md
  - 34-04-PLAN.md
---

# Cross-AI Plan Review — Phase 34

## Claude Review (independent session)

### Plan 01: Shared ActionItemList Component

**Summary.** Solid extraction plan with well-defined props, preserved styling details, and grep-verifiable acceptance criteria. The main gap is that mutation logic (toggleDone/assignTo) is duplicated in every consumer rather than extracted — the component shares rendering but not the fetch pattern.

**Strengths**
- Props interface correctly pushes data/callbacks up — no internal fetching in the shared component
- Specific Radix component choices (Checkbox, Select) with exact CSS dimensions (`h-7 w-36 text-xs`) prevent drift from existing ActionsPage
- Acceptance criteria are mechanically checkable (grep + tsc), not vague

**Concerns**
- **MEDIUM** — `toggleDone`/`assignTo` re-implemented in NoteViewer, PeoplePage, and RightPanel with the same PUT pattern. By the end of the phase this code will exist in 5+ files. A `useActionItems(notePath?)` hook would centralize it.
- **MEDIUM** — NoteViewer fetches all `/actions` then filters client-side. Fine for small brains, but no server-side filter param exists. Should be noted as a known limitation.
- **MEDIUM** — RightPanel instruction is ambiguous: "If RightPanel does not currently show note context, add a conditional section." Leaves structural decisions to the executor mid-task.
- **LOW** — No error handling on the PUT calls. Silent failure on network error.

**Suggestions**
- Clarify RightPanel: read the file during planning and state exactly what section to add and where.
- Note the fetch-all-then-filter limitation explicitly so it surfaces for Phase 35 optimization.
- `useActionItems` hook is borderline scope — defer to backlog since Plan 04 also re-implements the same pattern in IntelligencePage.

**Risk Assessment: LOW** — Well-specified, clean extraction. Ambiguity in RightPanel is the main execution risk.

---

### Plan 02: Cmd+K Command Palette

**Summary.** Clean, focused plan. Two files, one new dependency, clear acceptance criteria. Correctly defers Toaster mount here so downstream plans can call `toast.*` immediately.

**Strengths**
- Correct keyboard handling: `e.preventDefault()` + toggle on second Cmd+K
- Pinned package versions (cmdk@1.1.1, sonner@2.0.7) prevent install-time surprises
- Toaster mounted once at App level — avoids the multiple-Toaster-instance footgun
- cmdk's native filtering removes the need for manual search logic

**Concerns**
- **MEDIUM** — Note navigation calls `setCurrentPath(note.path)` but doesn't call `setCurrentView('notes')`. If user is on the People page, the note may not be displayed — navigation likely requires a view switch too.
- **MEDIUM** — With large note collections (1000+ notes), rendering all as `Command.Item`s in the same render pass may cause jank on palette open. cmdk filters but still renders them.
- **LOW** — pywebview may intercept Cmd+K at the webview level on some macOS configurations. `e.preventDefault()` handles the browser side but not the native shell.
- **LOW** — No loading state if `notes` array is empty when palette first opens.

**Suggestions**
- Add `setCurrentView('notes')` alongside `setCurrentPath()` in the note navigation handler.
- Consider slicing notes to top N (e.g., 200) for the palette render — full dataset is rarely needed for search.

**Risk Assessment: LOW** — Focused, clean plan. Navigation view-switch is the one real gap.

---

### Plan 03: Entity Create/Delete

**Summary.** Most complex plan in the phase. Backend is well-designed (correct cascade, reuses `forget_note`, explicit NULL clear on assignee_path). One structural conflict and one path encoding ambiguity need resolving before execution.

**Strengths**
- Cascade delete order is correct: NULL assignee_path → remove note_people → forget_note
- `forget_note()` delegation is right — it handles FTS, embeddings, and audit log
- Entity-specific dismiss labels ("Keep Person" / "Keep Meeting") are good UX copy
- `sb_create_person` MCP tool is minimal and correct — delegates to `capture_note()`

**Concerns**
- **HIGH** — **Wave 1 file conflict**: Plan 01 and Plan 03 both modify `PeoplePage.tsx`. The `execution_strategy: direct` frontmatter on both plans is correct, but the phase-level "Wave 1 (parallel)" label is wrong and misleading. If an executor reads the wave description before the frontmatter, they'll run these in parallel and produce a merge conflict.
- **MEDIUM** — The frontend DELETE call uses `encodeURIComponent(entityPath)` which encodes slashes. The Flask route uses `<path:note_path>` which expects literal slashes. The `_resolve_note_path` helper presumably handles decoded paths — but this roundtrip should be verified.
- **MEDIUM** — No new tests specified for the 6 new endpoints. Verification only checks existing tests pass. At minimum `POST /people` and `DELETE /people/<path>` need test coverage.
- **LOW** — Meeting/project cascade delete: meetings may have `note_people` rows linking them to people. Plan doesn't clear those before deleting — worth checking if `forget_note` handles it.
- **LOW** — `capture_note()` return type assumed to include `result["path"]` — verify this key exists in the actual return dict.

**Suggestions**
- Fix the wave label: Plan 02 is the only Wave 1 plan safe for parallel execution. Plans 01 → 03 must be sequential.
- Add path encoding test or verify `_resolve_note_path` handles URL-encoded slashes.
- Add at minimum one happy-path + one cascade test for the new endpoints.

**Risk Assessment: MEDIUM** — PeoplePage.tsx conflict risk is real if wave label is misread. Path encoding is a runtime footgun.

---

### Plan 04: Intelligence/TagAutocomplete/Toasts/Inbox

**Summary.** Wave 2 dependency on Plan 01 is correctly declared. TagAutocomplete design is solid. However, there is a real Python bug in the `/tags` fallback code, and the `files_modified` frontmatter is incomplete.

**Strengths**
- Fetch-once pattern for tag suggestions (ref flag) avoids hammering the API on every keystroke
- JSON fallback for tags is pragmatic given the Phase 32 junction table migration
- Keyboard navigation spec is complete (arrows wrap, Enter selects, Escape closes, mousedown click-outside)
- `toast.success` message distinguishes "Marked open" vs "Marked complete" — good detail

**Concerns**
- **HIGH** — **Stale connection bug in `/tags` fallback**: The fallback `conn.execute(...)` runs _after_ the `with get_connection() as conn:` block exits, meaning `conn` is already closed. This will raise a runtime error whenever `note_tags` is empty:
  ```python
  with get_connection() as conn:
      rows = conn.execute("SELECT DISTINCT tag FROM note_tags...").fetchall()
  tags = [r[0] for r in rows]
  if not tags:
      rows = conn.execute("SELECT tags FROM notes...")  # conn is CLOSED here
  ```
  Needs a second `with get_connection()` block or restructuring into a single block.
- **MEDIUM** — `files_modified` frontmatter lists 5 files but Task 2 also retroactively modifies NoteViewer.tsx, PeoplePage.tsx, and RightPanel.tsx to add toasts. Those aren't listed. Incomplete manifest means the file-conflict checker won't catch future conflicts.
- **MEDIUM** — InboxPage polish is "Claude's discretion" with only vague direction. Invitation for scope creep. Either specify exact changes or remove it.
- **LOW** — `toggleDone`/`assignTo` duplicated again in IntelligencePage — fourth implementation of the same 8-line pattern.
- **LOW** — `data.items || data.actions || []` defensive unpacking suggests the `/actions` response shape is ambiguous — worth normalizing the API response key once.

**Suggestions**
- Fix the stale connection bug before execution: merge both queries into one `with` block.
- Update `files_modified` to include NoteViewer.tsx, PeoplePage.tsx, RightPanel.tsx if the toast retrofix is kept.
- Either pin the Inbox changes (specific lines, specific components) or move them to a backlog item.

**Risk Assessment: MEDIUM** — Stale connection is a guaranteed runtime error on any fresh install that hasn't run Phase 32 migration.

---

## Consensus Summary

Single reviewer (claude, independent session). No divergent views to synthesize.

### Key Strengths
- Wave sequencing is correct (Plan 04 depends on Plan 01)
- Backend cascade delete is well-ordered and delegates correctly to `forget_note`
- Shared component design (ActionItemList) correctly inverts control to consumers
- Pinned dependency versions, mechanically-checkable acceptance criteria throughout

### Must-Fix Before Execution (HIGH)

1. **`/tags` stale connection bug (Plan 04)** — Guaranteed runtime error on fresh installs. Merge both SQL queries into one `with get_connection() as conn:` block.

2. **Wave 1 parallel label (Plan 03)** — Plans 01 and 03 both write `PeoplePage.tsx`. The label says Wave 1 parallel, but `execution_strategy: direct` says sequential. Correct the wave description to: Plan 02 runs independently; Plans 01 → 03 → 04 run sequentially.

### Recommended Execution Order
```
Plan 02 (CommandPalette) — independent, no shared files
Plan 01 (ActionItemList) — sequential
Plan 03 (Entity CRUD) — sequential, after 01
Plan 04 (Intelligence/Tags/Toasts) — sequential, after 01
```

### Lower-Priority Items (MEDIUM — fix or acknowledge)
- Plan 02: Add `setCurrentView('notes')` alongside `setCurrentPath()` in note navigation
- Plan 03: Verify `encodeURIComponent` path roundtrip with Flask `<path:>` route
- Plan 03: Add tests for new backend endpoints
- Plan 04: Update `files_modified` frontmatter to include toast-modified files
- All plans: `toggleDone`/`assignTo` duplicated 4x — backlog item for `useActionItems` hook
