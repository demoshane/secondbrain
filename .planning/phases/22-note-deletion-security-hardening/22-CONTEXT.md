# Phase 22: Note Deletion + Security Hardening - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can delete notes from the GUI with full cascade (file + DB + index + backlinks), and all note API endpoints are protected against path traversal attacks. Undo/recycle bin and soft-delete are out of scope.

</domain>

<decisions>
## Implementation Decisions

### Deletion trigger
- Red "Delete" button in the **viewer toolbar**, positioned on the right edge — visually separated from Edit/Save to prevent accidental clicks
- Delete button only visible in **view mode** (not edit mode)
- Deletes the **currently open note** — viewer is a prerequisite for deletion
- After successful API call: remove from sidebar **immediately (optimistic)** — do not wait for SSE event

### Confirmation modal
- Simple **"Are you sure?" modal** — copy the existing `#new-note-modal` pattern (fixed overlay, white box, 480px)
- Show the **note title/filename** prominently in the modal
- Warning text: "This will permanently delete the note and all its index entries."
- Buttons: red **"Delete"** (destructive) + grey **"Cancel"**
- If API call fails: show error message inside the modal, keep it open for retry

### File deletion
- Deletion MUST delete the actual `.md` file from disk — not just DB/index cleanup
- Cascade order: file → `notes` table → `note_embeddings` → `relationships` → `audit_log` → FTS5 rebuild
- Use `suppress_next_delete()` to prevent false-positive SSE event from watcher after programmatic delete

### Post-delete behavior
- Viewer shows brief **"Note deleted"** message (~2 seconds), then clears to welcome/blank state
- Sidebar selection clears entirely (no active item)
- Viewer content and editor both clear

### Claude's Discretion
- Exact duration/styling of the "Note deleted" transient message
- CSS for the red delete button in the toolbar
- Whether `delete_note()` utility lives in a new `engine/delete.py` or inline in `api.py`
- Exact FTS5 rebuild strategy (rebuild full vs. single-row delete trigger)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `#new-note-modal` pattern (index.html + app.js): copy for delete confirmation modal — overlay, white box, green/cancel buttons → change to red/cancel
- `suppress_next_delete(abs_path)` in `watcher.py`: call after `os.replace()` in delete endpoint to prevent FSEvents false positive
- `forget.py:forget_person()`: reference implementation for cascade delete pattern (file → DB → FTS5 rebuild order)
- `mcp_server.py:_issue_token()/_consume_token()`: NOT needed for GUI deletion — simple modal confirmation is sufficient for single-user GUI

### Established Patterns
- Paths via `pathlib.Path` throughout — no string concatenation for file paths
- `os.replace()` for atomic file writes (already used in save) — use `Path.unlink()` for deletion
- Error objects use `type(e).__name__` only — no file content in error messages (GDPR-05)
- Audit log: record deletion event with `event_type="delete_note"` and `note_path`

### Integration Points
- `engine/api.py`: add `DELETE /notes/<path>` route; add path traversal guard (`is_relative_to(brain_root)`) to all note routes
- `engine/gui/static/app.js`: add delete button click handler, modal open/close, DELETE fetch call, optimistic sidebar removal, transient message
- `engine/gui/static/index.html`: add delete modal HTML block + delete button in `#viewer-toolbar`
- `engine/watcher.py`: `suppress_next_delete()` already exists — call it from delete endpoint
- `engine/forget.py`: reference only — extract the cascade pattern but keep `delete_note()` as a separate utility

</code_context>

<specifics>
## Specific Ideas

- Delete button: red background, right edge of toolbar, visually separated from Edit/Save — "can't miss it but also can't accidentally hit it while editing"
- File MUST be deleted from disk (not just from DB) — this was explicitly called out

</specifics>

<deferred>
## Deferred Ideas

- Undo / recycle bin — would require soft-delete or backup; separate phase
- Bulk delete (select multiple notes) — separate phase
- Sidebar hover delete button (quick-delete without opening note) — deferred, toolbar-only for now

</deferred>

---

*Phase: 22-note-deletion-security-hardening*
*Context gathered: 2026-03-16*
