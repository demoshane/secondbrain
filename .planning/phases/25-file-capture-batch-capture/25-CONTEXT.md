# Phase 25: File Capture + Batch Capture - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

GUI file upload attached to specific notes (saved to `files/`, linked via new `attachments` table), visible as an attachment list below the note body in the viewer. A Batch Capture button in the sidebar captures all unindexed (absent from DB) markdown files in the brain directory, with results shown in the Intelligence panel. Watcher dedup guard prevents double-indexing when GUI upload and file watcher fire on the same path.

</domain>

<decisions>
## Implementation Decisions

### File Upload UX
- Upload button lives in the **sidebar toolbar**, next to the existing + new note button
- Supports both **file picker** (click button) and **drag-and-drop onto the viewer** while a note is open
- Accepted file types: **documents and images** (PDF, DOCX, PPTX, XLSX, TXT, JPG, PNG, GIF, WEBP, etc.) — reject executables and unknown binary types
- After upload: **silent success + sidebar/attachment list refresh** — no toast or modal

### Attachments UI
- Attachment list appears **below the note body** in the viewer (scroll down past note content)
- File entry shows: **filename + date + size** (e.g., "Q1-report.pdf · 2026-03-16 · 2.4 MB")
- Clicking a file entry in the attachment list opens the **file metadata in the viewer** (filename, size, date, type icon) with option to open in OS default app
- Upload button visible in the viewer when a note is open — attaches file to that specific note

### File-Only Notes
- No special note type — user creates a regular note, attaches a file. The note body IS the description.

### Attachment Data Model
- **New `attachments` table** in `brain.db`: `note_path`, `file_path`, `uploaded_at`
- Note-file relationship is DB-only (no frontmatter changes to existing notes)

### Batch Capture
- **GUI button in the sidebar toolbar** (alongside + new note and upload buttons)
- Targets: `.md` files in brain directory **absent from DB** (not yet in `notes` table) — already-indexed files skipped
- Result: **summary in Intelligence panel** — "Batch capture: 12 captured, 0 failed"; sidebar refreshes automatically
- Batch capture returns structured result: succeeded list + failed list with reason (per phase success criteria)

### Watcher Dedup Guard
- **DB check before index**: watcher checks if path already exists in `attachments` (for files) or `notes` (for .md files) table before processing — skip if already present
- Idempotent; no timing window dependency
- Extends the existing `suppress_next_delete()` pattern from Phase 21/22

### Unindexed Definition
- "Unindexed" = **absent from DB** (`notes` table has no row for that path)
- Modified-but-already-indexed files are NOT re-captured by batch capture

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `engine/watcher.py` — `BrainFileHandler` watches `files/` with debounce + batch timer. Same pattern can be extended or reused for the dedup DB check on file events.
- `engine/watcher.py` — `suppress_next_delete()` is the precedent for watcher suppression; dedup guard extends this pattern.
- `engine/capture.py` — `capture_note()` handles slug collision detection via DB check. Batch capture can reuse this for each unindexed .md file.
- `engine/reindex.py` — `reindex_brain()` walks all .md files and upserts; batch capture is a lighter version (absent-from-DB only, no full rebuild).
- `engine/api.py` — `/files` GET and `/files/move` POST already exist. New `POST /files/upload` endpoint needed. `/notes/<path>/attachments` GET/POST endpoints needed.
- `engine/gui/static/app.js` — Vanilla JS, no framework. File upload via `<input type="file">` + `FormData` + `fetch()`. Drag-and-drop via `dragover`/`drop` events on the viewer area.

### Established Patterns
- Backend is authoritative for data transformation (Phase 20)
- Vanilla JS only — no framework (Phase 21)
- Silent success + sidebar refresh — same pattern as note creation
- `suppress_next_delete()` for watcher suppression — extend this pattern
- Three-panel layout: sidebar / viewer / intelligence (fixed — don't add panels)

### Integration Points
- New `POST /files/upload` endpoint — receives file, saves to `files/`, inserts into `attachments` table, returns attachment record
- New `GET /notes/<path>/attachments` endpoint — returns attachments for a note
- New `POST /batch-capture` endpoint — finds unindexed .md files, captures each, returns structured result
- `attachments` table schema: `id INTEGER PK, note_path TEXT, file_path TEXT, filename TEXT, size INTEGER, uploaded_at TEXT`
- Intelligence panel: new message type for batch capture results (alongside existing recap/actions/connections messages)
- Sidebar toolbar: add upload button + batch capture button alongside existing + new note button

</code_context>

<specifics>
## Specific Ideas

- Files are **per-note attachments**, not a global file library — this is the core mental model
- A "file-only" note is just a regular note whose body serves as the description; no new note type
- Batch capture is the "catch-up" tool for markdown files that exist in brain dir but were never indexed (e.g., files dropped in directly via Finder before the watcher was running)

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 25-file-capture-batch-capture*
*Context gathered: 2026-03-16*
