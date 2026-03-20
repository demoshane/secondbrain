# Phase 25: File Capture + Batch Capture - Research

**Researched:** 2026-03-16
**Domain:** Flask file upload, SQLite schema migration, watcher dedup, vanilla JS drag-and-drop
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**File Upload UX**
- Upload button lives in the sidebar toolbar, next to the existing + new note button
- Supports both file picker (click button) and drag-and-drop onto the viewer while a note is open
- Accepted file types: documents and images (PDF, DOCX, PPTX, XLSX, TXT, JPG, PNG, GIF, WEBP, etc.) — reject executables and unknown binary types
- After upload: silent success + sidebar/attachment list refresh — no toast or modal

**Attachments UI**
- Attachment list appears below the note body in the viewer (scroll down past note content)
- File entry shows: filename + date + size (e.g., "Q1-report.pdf · 2026-03-16 · 2.4 MB")
- Clicking a file entry in the attachment list opens the file metadata in the viewer (filename, size, date, type icon) with option to open in OS default app
- Upload button visible in the viewer when a note is open — attaches file to that specific note

**File-Only Notes**
- No special note type — user creates a regular note, attaches a file. The note body IS the description.

**Attachment Data Model**
- New `attachments` table in `brain.db`: `note_path`, `file_path`, `uploaded_at`
- Note-file relationship is DB-only (no frontmatter changes to existing notes)

**Batch Capture**
- GUI button in the sidebar toolbar (alongside + new note and upload buttons)
- Targets: `.md` files in brain directory absent from DB (not yet in `notes` table) — already-indexed files skipped
- Result: summary in Intelligence panel — "Batch capture: 12 captured, 0 failed"; sidebar refreshes automatically
- Batch capture returns structured result: succeeded list + failed list with reason

**Watcher Dedup Guard**
- DB check before index: watcher checks if path already exists in `attachments` (for files) or `notes` (for .md files) table before processing — skip if already present
- Idempotent; no timing window dependency
- Extends the existing `suppress_next_delete()` pattern from Phase 21/22

**Unindexed Definition**
- "Unindexed" = absent from DB (`notes` table has no row for that path)
- Modified-but-already-indexed files are NOT re-captured by batch capture

### Claude's Discretion

None specified — all implementation decisions locked in CONTEXT.md.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GUIF-01 | User can capture a file from the GUI or by pointing sb-capture at an external file path; file saved to files/ and indexed | Flask `request.files`, `werkzeug` secure_filename, `attachments` table, `POST /files/upload`, drag-and-drop via JS dragover/drop events, hidden `<input type="file">` |
| ENGL-01 | A single capture trigger captures all relevant new items in batch (not just the first) | `POST /batch-capture` endpoint walking brain dir, `reindex_brain()` pattern minus the upsert (insert-only for absent paths), structured result dict |
</phase_requirements>

---

## Summary

Phase 25 adds two distinct capabilities on top of the existing Flask+SQLite+vanilla-JS stack: (1) per-note file attachments stored in `files/` with a new `attachments` DB table, and (2) a batch capture endpoint that indexes all untracked markdown files in one shot.

The codebase is well-understood after 24 prior phases. All primitives exist: atomic file writes (`write_note_atomic`), slug-collision-safe note creation (`capture_note`), watcher suppression (`suppress_next_delete`), and a reindex walker (`reindex_brain`). The main new surface is the `attachments` table (DB migration required), three new API endpoints, and frontend additions to the sidebar toolbar and viewer.

The watcher dedup guard is a DB-check approach (idempotent, no timing window) rather than a suppression-window approach, which is simpler and more reliable. It extends the existing pattern without replacing it.

**Primary recommendation:** Add `attachments` table via an `engine/db.py` migration function; implement three endpoints in `engine/api.py`; add upload button + batch capture button to the sidebar toolbar and attachment list below the viewer; patch `NoteChangeHandler._fire` to skip already-indexed paths.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask | existing | New endpoints: POST /files/upload, GET /notes/<path>/attachments, POST /batch-capture | Already the app server |
| werkzeug | existing (Flask dep) | `secure_filename()` for upload sanitization | Standard Flask upload pattern |
| sqlite3 | stdlib | `attachments` table insert/select | Already used throughout |
| python-frontmatter | existing | Parse .md files in batch capture | Already used in reindex |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib.Path | stdlib | All file path operations | All new file handling |
| mimetypes | stdlib | Detect MIME type for upload validation | Reject executables/unknown binary |
| os.path / shutil | stdlib | Save uploaded bytes to files/ | Upload storage |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| DB-check dedup guard | timing-window suppression (like suppress_next_delete) | DB check is idempotent and race-free; suppression window can miss fast back-to-back events |
| `mimetypes` stdlib | python-magic (libmagic) | mimetypes is zero-dep and adequate for extension-based validation; magic would need an extra dep |

**Installation:** No new dependencies required.

---

## Architecture Patterns

### Recommended Project Structure

New files:
```
engine/
├── attachments.py       # save_attachment(), list_attachments(), DB migration
tests/
├── test_attachments.py  # unit tests for attachments module
├── test_api_upload.py   # API tests: POST /files/upload, GET attachments, POST /batch-capture
```

Modified files:
```
engine/db.py             # add migrate_add_attachments_table()
engine/api.py            # 3 new endpoints
engine/watcher.py        # dedup guard in NoteChangeHandler._fire
engine/gui/static/index.html  # upload button + batch capture button in toolbar
engine/gui/static/app.js      # upload handler, drag-and-drop, attachment list render, batch capture
```

### Pattern 1: Flask File Upload
**What:** Receive multipart form data, save bytes to `files/`, insert into `attachments` table.
**When to use:** `POST /files/upload` endpoint.
**Example:**
```python
# Source: Flask docs — werkzeug secure_filename pattern
from werkzeug.utils import secure_filename
import mimetypes

ALLOWED_MIMES = {
    'application/pdf', 'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/plain', 'image/jpeg', 'image/png', 'image/gif', 'image/webp',
}

@app.post("/files/upload")
def upload_file():
    note_path = request.form.get("note_path", "")
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "no file"}), 400
    mime = mimetypes.guess_type(f.filename)[0] or ""
    if mime not in ALLOWED_MIMES:
        return jsonify({"error": "file type not allowed"}), 415
    filename = secure_filename(f.filename)
    brain_path = os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain"))
    dest = Path(brain_path) / "files" / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    f.save(str(dest))
    # Insert into attachments table + suppress watcher duplicate
    ...
```

### Pattern 2: Watcher Dedup Guard
**What:** Before processing a newly-seen file path in `NoteChangeHandler._fire`, check DB for existing row.
**When to use:** In `NoteChangeHandler._fire` for `created` events on paths in `files/` segment; or for `.md` note paths.
**Example:**
```python
# engine/watcher.py — extend _fire() for dedup
def _fire(self, event_type: str, src_path: str) -> None:
    with self._lock:
        self._timers.pop(src_path, None)
    if event_type == "deleted":
        with _save_suppress_lock:
            if src_path in _save_suppress:
                return
    # Dedup guard for created events: skip if already in DB
    if event_type == "created":
        from engine.db import get_connection
        conn = get_connection()
        already = conn.execute(
            "SELECT 1 FROM notes WHERE path=?", (src_path,)
        ).fetchone()
        conn.close()
        if already:
            return
    ...
```

### Pattern 3: Batch Capture Endpoint
**What:** Walk brain dir for `.md` files absent from `notes` table; call `capture_note` or direct-insert for each; return structured result.
**When to use:** `POST /batch-capture`.
**Example:**
```python
@app.post("/batch-capture")
def batch_capture():
    brain_path = os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain"))
    brain_root = Path(brain_path)
    conn = get_connection()
    existing = {
        row[0]
        for row in conn.execute("SELECT path FROM notes").fetchall()
    }
    succeeded = []
    failed = []
    for md_path in sorted(brain_root.rglob("*.md")):
        abs_str = str(md_path.resolve())
        if abs_str in existing:
            continue  # already indexed — skip
        try:
            post = _fm.loads(md_path.read_text(encoding="utf-8"))
            # ... insert into notes table ...
            succeeded.append(abs_str)
        except Exception as e:
            failed.append({"path": abs_str, "reason": type(e).__name__})
    conn.commit()
    conn.close()
    _broadcast({"type": "created", "path": ""})  # trigger sidebar refresh
    return jsonify({"succeeded": succeeded, "failed": failed})
```

### Pattern 4: Vanilla JS File Upload + Drag-and-Drop
**What:** Hidden `<input type="file">`, triggered by button click; `dragover`/`drop` on viewer area; `FormData` + `fetch`.
**When to use:** Upload button in sidebar toolbar; drag target = `#viewer` div.
**Example:**
```javascript
// Hidden input triggered by button
document.getElementById('upload-btn').addEventListener('click', () => {
    document.getElementById('file-input').click();
});
document.getElementById('file-input').addEventListener('change', e => {
    const file = e.target.files[0];
    if (file && currentPath) uploadFile(file);
    e.target.value = '';  // reset so same file can be re-selected
});

// Drag-and-drop on viewer
const viewer = document.getElementById('viewer');
viewer.addEventListener('dragover', e => { e.preventDefault(); });
viewer.addEventListener('drop', e => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && currentPath) uploadFile(file);
});

async function uploadFile(file) {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('note_path', currentPath);
    const res = await fetch(`${API}/files/upload`, { method: 'POST', body: fd });
    if (res.ok) {
        await loadAttachments(currentPath);
        await loadNotes();
    }
}
```

### Pattern 5: attachments DB Migration
**What:** Add `attachments` table via a migration function called from `init_schema`.
**When to use:** `engine/db.py` — follow existing migration function pattern.
**Example:**
```python
def migrate_add_attachments_table(conn: sqlite3.Connection) -> None:
    """Idempotent migration: create attachments table if absent."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attachments (
            id          INTEGER PRIMARY KEY,
            note_path   TEXT NOT NULL,
            file_path   TEXT NOT NULL,
            filename    TEXT NOT NULL,
            size        INTEGER NOT NULL DEFAULT 0,
            uploaded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
    """)
    conn.commit()
```
Then call `migrate_add_attachments_table(conn)` at the end of `init_schema()`.

### Anti-Patterns to Avoid
- **Storing attachments in frontmatter:** Locked decision is DB-only. Adding YAML fields would break existing note parsing and the "no frontmatter changes" constraint.
- **Using suppress_next_delete() for upload dedup:** That approach has a timing window. The DB check is race-free because the GUI endpoint inserts before returning.
- **Calling reindex_brain() for batch capture:** reindex upserts all files (including already-indexed ones) and triggers embeddings. Batch capture must be insert-only for absent paths and must not rebuild the full FTS5 index.
- **Building MIME detection from scratch:** Use `mimetypes.guess_type()` on filename. Do not inspect file magic bytes unless mimetypes is insufficient — adding python-magic is unnecessary complexity.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Filename sanitization | Custom regex stripping | `werkzeug.utils.secure_filename` | Handles path separators, null bytes, reserved names |
| MIME type detection | Manual extension map | `mimetypes.guess_type()` stdlib | Covers all needed types; zero deps |
| Atomic temp-file write for notes | Direct write then rename | `write_note_atomic()` already in capture.py | Already handles FD cleanup, DB-commit-before-rename ordering |

---

## Common Pitfalls

### Pitfall 1: Watcher fires before DB insert completes
**What goes wrong:** GUI uploads file → watcher fires `created` event → dedup DB check runs before `INSERT INTO attachments` commits → watcher treats file as new → creates a duplicate note.
**Why it happens:** `f.save()` writes the file to disk synchronously; the watcher fires on the OS `created` event before the API handler inserts into DB.
**How to avoid:** Insert into `attachments` table and commit BEFORE calling `f.save()` — or at minimum, suppress the watcher event for the uploaded file path using `suppress_next_delete`-style mechanism in addition to the DB check. The safest approach is to do both: insert first (so DB check always wins), and add the path to a suppress set.
**Warning signs:** Test that uploads two files in quick succession and checks the `attachments` table count.

### Pitfall 2: secure_filename strips directory structure to empty string
**What goes wrong:** `secure_filename("../evil.sh")` returns `"evil.sh"` (good), but `secure_filename("../../")` returns `""` (empty string). If filename is empty, `dest` path becomes `files/` directory itself.
**Why it happens:** werkzeug secure_filename strips all path components.
**How to avoid:** Check `if not filename: return jsonify({"error": "invalid filename"}), 400` after calling `secure_filename`.

### Pitfall 3: Batch capture re-indexes modified files
**What goes wrong:** User calls batch capture on a brain that has notes already indexed — all previously-indexed notes get re-indexed, updating `updated_at` timestamps and triggering FTS5 rebuild.
**Why it happens:** Using `reindex_brain()` or an UPSERT instead of an INSERT-only pattern.
**How to avoid:** Check `abs_str in existing` (set of paths already in `notes` table) before attempting any insert. Skip — do not upsert.

### Pitfall 4: Attachment list renders before note body
**What goes wrong:** Viewer shows attachment list but note body is blank on first open; or vice versa.
**Why it happens:** `openNote()` and `loadAttachments()` are separate async calls; if `loadAttachments` resolves first and overwrites innerHTML, the note body is lost.
**How to avoid:** Load note body first (await), append attachment list DOM nodes below — never overwrite `#viewer` innerHTML when rendering attachments. Use a separate `#attachments-section` div appended after `#viewer` content.

### Pitfall 5: Duplicate filename collision in files/
**What goes wrong:** Two notes attach a file with the same name → second upload overwrites first.
**Why it happens:** Both save to `files/<filename>`.
**How to avoid:** Use a per-note subdirectory `files/<note_slug>/` or append a counter suffix on collision (check `dest.exists()` before saving). The simpler approach is counter suffix: `report.pdf` → `report-2.pdf`.

### Pitfall 6: get_connection() opens a new DB connection per watcher event
**What goes wrong:** Watcher dedup check opens a connection on every file system event, creating many short-lived connections under load.
**Why it happens:** Watcher runs in a background thread; no shared connection pool.
**How to avoid:** The existing codebase already uses this pattern (get_connection + close per operation). It is acceptable here — SQLite WAL mode handles concurrent readers safely. Keep the same pattern for consistency.

---

## Code Examples

### Existing: `suppress_next_delete` pattern (extend this for upload dedup)
```python
# engine/watcher.py — existing suppression set pattern
_save_suppress: set[str] = set()
_save_suppress_lock = threading.Lock()

def suppress_next_delete(abs_path: str, window: float = 0.5) -> None:
    with _save_suppress_lock:
        _save_suppress.add(abs_path)
    threading.Timer(window, _clear_suppress, args=(abs_path,)).start()
```
Use the same pattern to add a `suppress_next_create` (or re-use the same set keyed by path) for upload dedup, in addition to the DB check.

### Existing: `capture_note` slug collision guard (reusable in batch capture)
```python
# engine/capture.py — slug collision pattern
while target.exists() or conn.execute(
    "SELECT 1 FROM notes WHERE path=?", (str(target.resolve()),)
).fetchone():
    target = brain_root / subdir / f"{slug}-{counter}.md"
    counter += 1
```
Batch capture must respect the same collision detection — do not insert a path that already exists on disk even if absent from DB.

### Existing: `_broadcast` for sidebar refresh
```python
# engine/api.py — trigger sidebar reload after batch capture
_broadcast({"type": "created", "path": ""})
```
Call this at the end of `POST /batch-capture` to refresh all connected GUIs.

### Existing: `init_schema` migration pattern
```python
# engine/db.py — call new migration at end of init_schema
def init_schema(conn: sqlite3.Connection, reset: bool = False) -> None:
    ...
    conn.executescript(SCHEMA_SQL)
    migrate_add_people_column(conn)
    migrate_add_action_items_table(conn)
    migrate_add_attachments_table(conn)  # new
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| suppress_next_delete timing window | DB-check dedup (idempotent) | Phase 25 (new) | Eliminates race condition for upload dedup |
| No batch indexing | POST /batch-capture insert-only walk | Phase 25 (new) | ENGL-01 satisfied without full reindex cost |

---

## Open Questions

1. **Should upload also suppress the watcher `created` event, or rely solely on the DB check?**
   - What we know: DB check is idempotent. But if watcher fires before the DB INSERT commits (tiny window), a duplicate note could be created.
   - What's unclear: How fast does macOS FSEvents deliver `created` events relative to Flask response time?
   - Recommendation: Use both — insert into `attachments` DB first, AND add path to a `_upload_suppress` set (same pattern as `_save_suppress`). Belt-and-suspenders.

2. **Where does the upload button live — sidebar toolbar or viewer toolbar?**
   - CONTEXT.md says: sidebar toolbar AND viewer toolbar (both). Sidebar button = global file upload attached to currently-open note. Viewer button = same action, just scoped to current note.
   - Recommendation: Both locations point to the same `uploadFile(file)` function; both require `currentPath` to be set.

3. **File size limit for uploads?**
   - Not specified in CONTEXT.md.
   - Recommendation: Set Flask `MAX_CONTENT_LENGTH = 50 * 1024 * 1024` (50 MB). Return 413 if exceeded. Log a note in the plan but do not block on this — default Flask behavior is no limit.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing, pyproject.toml) |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_api_upload.py -x -q` |
| Full suite command | `uv run pytest tests/ -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GUIF-01 | POST /files/upload saves file to files/ dir | unit | `uv run pytest tests/test_api_upload.py::TestFileUpload::test_upload_saves_file -x` | Wave 0 |
| GUIF-01 | POST /files/upload inserts into attachments table | unit | `uv run pytest tests/test_api_upload.py::TestFileUpload::test_upload_inserts_attachment_row -x` | Wave 0 |
| GUIF-01 | POST /files/upload rejects executable MIME types | unit | `uv run pytest tests/test_api_upload.py::TestFileUpload::test_upload_rejects_executable -x` | Wave 0 |
| GUIF-01 | GET /notes/<path>/attachments returns list for note | unit | `uv run pytest tests/test_api_upload.py::TestAttachmentsList::test_list_attachments -x` | Wave 0 |
| ENGL-01 | POST /batch-capture indexes absent .md files | unit | `uv run pytest tests/test_api_upload.py::TestBatchCapture::test_batch_captures_unindexed -x` | Wave 0 |
| ENGL-01 | POST /batch-capture skips already-indexed files | unit | `uv run pytest tests/test_api_upload.py::TestBatchCapture::test_batch_skips_indexed -x` | Wave 0 |
| ENGL-01 | POST /batch-capture returns structured succeeded/failed result | unit | `uv run pytest tests/test_api_upload.py::TestBatchCapture::test_batch_returns_structured_result -x` | Wave 0 |
| GUIF-01 + ENGL-01 | Watcher dedup: uploading via GUI does not create duplicate when watcher also fires | unit | `uv run pytest tests/test_note_watcher.py::TestWatcherDedup -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_api_upload.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_api_upload.py` — covers GUIF-01 and ENGL-01 API endpoints
- [ ] `TestWatcherDedup` class in `tests/test_note_watcher.py` — covers upload dedup guard (file exists; class is new)

---

## Sources

### Primary (HIGH confidence)
- Direct code reading: `engine/watcher.py`, `engine/capture.py`, `engine/api.py`, `engine/db.py`, `engine/reindex.py` — all patterns verified from source
- Direct code reading: `engine/gui/static/index.html`, `engine/gui/static/app.js` — UI structure and existing toolbar pattern verified
- `tests/test_api.py` — test fixture pattern (Flask test client, monkeypatch BRAIN_PATH, tmp_path) verified from source

### Secondary (MEDIUM confidence)
- Flask file upload pattern: werkzeug `secure_filename` is the documented standard for Flask file uploads (Flask docs)
- `mimetypes.guess_type()`: Python stdlib, documented behavior for extension-based MIME detection

### Tertiary (LOW confidence)
- macOS FSEvents timing relative to Flask response: assumed sub-100ms, not measured. Belt-and-suspenders dedup recommended as mitigation.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use; no new deps
- Architecture patterns: HIGH — derived directly from existing code
- Pitfalls: HIGH (timing pitfall is MEDIUM) — most pitfalls derived from code reading; FSEvents timing is estimated
- Test map: HIGH — follows exact existing pytest fixture and class patterns

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (stable stack, no external dependencies changing)
