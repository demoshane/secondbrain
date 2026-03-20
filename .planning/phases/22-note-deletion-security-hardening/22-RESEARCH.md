# Phase 22: Note Deletion + Security Hardening — Research

**Researched:** 2026-03-16
**Domain:** Flask REST API, SQLite cascade delete, JS modal/UX, path traversal security
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Delete button in the viewer toolbar, right edge, visible in view mode only
- Optimistic sidebar removal after successful API call (do not wait for SSE)
- Simple "Are you sure?" modal — copy `#new-note-modal` pattern (fixed overlay, white box, 480px)
- Show note title/filename in modal; warning text: "This will permanently delete the note and all its index entries."
- Buttons: red "Delete" + grey "Cancel"; on API failure: show error in modal, keep it open
- File MUST be deleted from disk (`Path.unlink()`), not just DB/index
- Cascade order: file → `notes` table → `note_embeddings` → `relationships` → `audit_log` → FTS5 rebuild
- Call `suppress_next_delete(abs_path)` before `Path.unlink()` to prevent false-positive SSE event
- Post-delete: viewer shows "Note deleted" message (~2s), then clears to blank state; sidebar selection clears; editor clears
- Add `is_relative_to(brain_root)` path traversal guard to all note routes in `api.py`

### Claude's Discretion
- Exact duration/styling of the "Note deleted" transient message
- CSS for the red delete button in the toolbar
- Whether `delete_note()` utility lives in a new `engine/delete.py` or inline in `api.py`
- Exact FTS5 rebuild strategy (full rebuild vs. single-row delete trigger)

### Deferred Ideas (OUT OF SCOPE)
- Undo / recycle bin
- Bulk delete
- Sidebar hover delete button (quick-delete without opening note)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GUIX-06 | User can delete a note from the GUI; deletion cascades to backlinks and FTS5 index | Cascade pattern fully documented in `forget.py`; modal pattern in `index.html`/`app.js`; path traversal guard via `Path.is_relative_to()` |
</phase_requirements>

---

## Summary

Phase 22 adds a destructive write operation (DELETE) to the GUI. All the necessary building blocks already exist in the codebase: the cascade order is established in `forget.py`, the `suppress_next_delete()` mechanism is live in `watcher.py`, the modal HTML/CSS pattern is in `index.html`/`style.css`, and the Flask route structure is in `api.py`. The work is mostly assembly and hardening rather than greenfield development.

The security hardening (path traversal guard) is a one-line addition per route: `p.resolve().is_relative_to(brain_root.resolve())` — returning 403 on failure. This must be applied uniformly to `GET /notes/<path>`, `PUT /notes/<path>`, `DELETE /notes/<path>`, and `GET /notes/<path>/meta`.

The FTS5 situation is important: the schema already has `notes_ad` AFTER DELETE trigger that issues a shadow-table tombstone for FTS5. This means `DELETE FROM notes` already keeps FTS5 internally consistent without a full rebuild. A full `INSERT INTO notes_fts(notes_fts) VALUES('rebuild')` is safe but unnecessary for single-row deletes; the trigger handles it. The planner should use the trigger path (no explicit rebuild) for performance, but a full rebuild is an acceptable fallback if there are concerns about stale shadow rows.

**Primary recommendation:** Assemble `delete_note(abs_path, conn, brain_root)` in `engine/delete.py`, call it from `DELETE /notes/<path>`, add `is_relative_to` guards to all four affected routes, and wire the JS modal following the `#new-note-modal` clone pattern.

---

## Standard Stack

### Core — already in project
| Library/Tool | Version | Purpose | Notes |
|---|---|---|---|
| Flask | installed | `DELETE /notes/<path>` route | Use `@app.delete` decorator |
| SQLite3 + FTS5 | stdlib | Cascade delete + index | `notes_ad` trigger handles FTS5 automatically |
| pathlib.Path | stdlib | All file operations | `Path.unlink()` for delete; `Path.resolve().is_relative_to()` for guard |
| `suppress_next_delete` | watcher.py | Prevent false-positive SSE | Already imported in api.py |

### No New Dependencies
Everything needed is already installed. Do not add any new packages.

---

## Architecture Patterns

### Recommended File Structure
```
engine/
├── delete.py          # NEW: delete_note() utility (or inline in api.py — discretion)
├── api.py             # add DELETE route + is_relative_to guard on 4 routes
└── gui/static/
    ├── index.html     # add #delete-note-modal block + #delete-btn in toolbar
    ├── app.js         # add delete button logic, modal, optimistic removal
    └── style.css      # add #delete-btn red style, #delete-note-modal rules
tests/
└── test_delete.py     # NEW: unit tests for delete_note() + route
```

### Pattern 1: delete_note() Utility
**What:** Single shared function that performs cascade delete for one note.
**When to use:** Called by both `DELETE /notes/<path>` API route and (optionally) `sb-forget` CLI for notes.
**Reference:** Mirrors `forget_person()` cascade order from `engine/forget.py` lines 83–129.

```python
# engine/delete.py
def delete_note(abs_path: Path, conn, brain_root: Path) -> dict:
    """Delete a single note: file + DB cascade + FTS5 (via trigger) + audit log."""
    path_str = str(abs_path.resolve())

    # 1. Suppress watcher BEFORE unlink to avoid false-positive SSE
    from engine.watcher import suppress_next_delete
    suppress_next_delete(path_str)

    # 2. Delete file from disk
    abs_path.unlink(missing_ok=True)

    # 3. Delete from notes (notes_ad trigger handles FTS5 shadow tombstone)
    conn.execute("DELETE FROM notes WHERE path=?", (path_str,))

    # 4. Delete from note_embeddings
    conn.execute("DELETE FROM note_embeddings WHERE note_path=?", (path_str,))

    # 5. Delete from relationships (both directions)
    conn.execute(
        "DELETE FROM relationships WHERE source_path=? OR target_path=?",
        (path_str, path_str),
    )

    # 6. Delete from audit_log (GDPR consistency)
    conn.execute("DELETE FROM audit_log WHERE note_path=?", (path_str,))

    # 7. Audit log: record delete event (note_path=NULL so it is never self-deleted)
    conn.execute(
        "INSERT INTO audit_log (event_type, note_path, detail, created_at) VALUES (?,?,?,?)",
        ("delete_note", None, path_str, datetime.datetime.utcnow().isoformat()),
    )
    conn.commit()
    return {"deleted": True, "path": path_str}
```

### Pattern 2: Flask DELETE Route with Path Traversal Guard
**What:** `DELETE /notes/<path:note_path>` with `is_relative_to` check.
**When to use:** This guard pattern MUST be applied to all four note routes.

```python
# engine/api.py — helper (call at top of each affected route)
import os as _os

def _resolve_note_path(note_path: str) -> tuple[Path, Path]:
    """Return (abs_path, brain_root). Raises ValueError if path escapes brain_root."""
    brain_root = Path(_os.environ.get("BRAIN_PATH", _os.path.expanduser("~/SecondBrain"))).resolve()
    p = (Path(note_path) if note_path.startswith("/") else Path("/") / note_path).resolve()
    if not p.is_relative_to(brain_root):
        raise ValueError("path traversal")
    return p, brain_root


@app.delete("/notes/<path:note_path>")
def delete_note_endpoint(note_path):
    try:
        p, brain_root = _resolve_note_path(note_path)
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    if not p.exists():
        return jsonify({"error": "Not found"}), 404
    from engine.delete import delete_note
    conn = get_connection()
    try:
        result = delete_note(p, conn, brain_root)
    except Exception as e:
        conn.close()
        return jsonify({"error": type(e).__name__}), 500
    conn.close()
    return jsonify(result), 200
```

### Pattern 3: JS Modal Clone
**What:** Clone `#new-note-modal` pattern for delete confirmation.
**Key difference:** No form fields — just title display, warning text, two buttons.

```html
<!-- index.html — add after #new-note-modal block -->
<div id="delete-note-modal" style="display:none">
  <div id="delete-modal-content">
    <h2>Delete Note</h2>
    <p id="delete-modal-filename" style="font-weight:bold"></p>
    <p>This will permanently delete the note and all its index entries.</p>
    <span id="delete-modal-error" style="color:red;display:none"></span>
    <button id="delete-modal-confirm">Delete</button>
    <button id="delete-modal-cancel">Cancel</button>
  </div>
</div>
```

```javascript
// app.js — delete flow
document.getElementById('delete-btn').addEventListener('click', () => {
    if (!currentPath) return;
    const filename = currentPath.split('/').pop();
    document.getElementById('delete-modal-filename').textContent = filename;
    document.getElementById('delete-modal-error').style.display = 'none';
    document.getElementById('delete-note-modal').style.display = 'flex';
});

document.getElementById('delete-modal-cancel').addEventListener('click', () => {
    document.getElementById('delete-note-modal').style.display = 'none';
});

document.getElementById('delete-modal-confirm').addEventListener('click', async () => {
    const pathToDelete = currentPath;
    const res = await fetch(`${API}/notes/${encodeURIComponent(pathToDelete)}`, { method: 'DELETE' });
    if (!res.ok) {
        const errEl = document.getElementById('delete-modal-error');
        errEl.textContent = 'Delete failed. Please try again.';
        errEl.style.display = '';
        return;
    }
    // Optimistic: remove from sidebar immediately
    document.getElementById('delete-note-modal').style.display = 'none';
    document.querySelectorAll(`#note-list li[data-path="${pathToDelete}"]`).forEach(el => el.remove());
    currentPath = null;
    exitEditMode();
    // Show transient "Note deleted" message, then clear viewer
    const viewer = document.getElementById('viewer');
    viewer.innerHTML = '<em>Note deleted.</em>';
    setTimeout(() => { viewer.innerHTML = ''; }, 2000);
    loadNotes(); // background refresh to sync count
});
```

### Pattern 4: Delete Button in Viewer Toolbar
```html
<!-- index.html — inside #viewer-toolbar, right side -->
<button id="delete-btn" style="margin-left:auto">Delete</button>
```

```css
/* style.css */
#delete-btn { background: #e74c3c; color: #fff; border-color: #c0392b; margin-left: auto; }
#delete-btn:hover { background: #c0392b; }
#delete-note-modal { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
#delete-modal-content { background: #fff; border-radius: 8px; padding: 24px; width: 480px; display: flex; flex-direction: column; gap: 12px; }
#delete-modal-confirm { background: #e74c3c; color: #fff; border: none; border-radius: 4px; padding: 8px 16px; cursor: pointer; font-size: 13px; }
#delete-modal-cancel { background: #e0e0e0; border: none; border-radius: 4px; padding: 8px 16px; cursor: pointer; font-size: 13px; }
```

**Delete button visibility:** Hide in edit mode via `exitEditMode()` / `enterEditMode()`. Add `document.getElementById('delete-btn').style.display` toggling alongside the existing `edit-btn`/`save-btn` pattern.

### Anti-Patterns to Avoid
- **Deleting from DB before disk:** If `unlink()` fails after DB delete, note is gone from index but file persists — orphan on disk. Delete file first.
- **Not calling `suppress_next_delete` before `unlink()`:** Will fire a false-positive `deleted` SSE event to the open browser tab, causing the already-running JS handler to also try to clear the UI — double clear.
- **Calling `is_relative_to` on unresolved paths:** Symlinks can bypass the check. Always call `.resolve()` on both the path and `brain_root` before `is_relative_to()`.
- **String concatenation for paths:** The codebase uses `pathlib.Path` throughout — maintain that.
- **Putting file content in error messages:** GDPR-05 — only `type(e).__name__` in error responses.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| FTS5 index cleanup | Manual shadow-table delete | `notes_ad` AFTER DELETE trigger (already in schema) | Trigger fires automatically on `DELETE FROM notes`; manual shadow ops risk desync |
| Path canonicalization | String prefix checks | `Path.resolve().is_relative_to()` | Symlinks and `../` sequences defeat string checks |
| Atomic watcher suppression | Custom threading.Event | `suppress_next_delete()` (already in watcher.py) | Already handles thread-safe set + timed clear |
| Modal overlay | Custom CSS from scratch | Clone `#new-note-modal` + `#modal-content` rules | Identical layout; change IDs and button colors only |

---

## Common Pitfalls

### Pitfall 1: FTS5 Rebuild Not Needed for Single-Row Delete
**What goes wrong:** Phase plans a full `INSERT INTO notes_fts(notes_fts) VALUES('rebuild')` after every delete, causing a full index scan on every note deletion.
**Why it happens:** `forget_person()` uses full rebuild as a safety net for multi-row GDPR erasure; devs copy that pattern.
**How to avoid:** The schema's `notes_ad` AFTER DELETE trigger handles the FTS5 tombstone automatically. A full rebuild is only needed after bulk operations or when shadow rows may be stale. For a single-note delete, skip the explicit rebuild.
**Warning signs:** Performance regression on large brains; every delete taking 100ms+.

### Pitfall 2: SSE Double-Clear on Delete
**What goes wrong:** After the DELETE API call succeeds, the watcher fires a `deleted` FSEvent for the unlinked file. The JS `handleNoteEvent` handler sees `type === 'deleted'` for `currentPath` (which is now `null`) — harmless but still worth suppressing.
**Why it happens:** `suppress_next_delete()` must be called BEFORE `Path.unlink()`, not after.
**How to avoid:** Order in `delete_note()`: `suppress_next_delete(path_str)` → `abs_path.unlink()`.

### Pitfall 3: Path Traversal via Double-Slash or URL Encoding
**What goes wrong:** Attacker sends `DELETE /notes/..%2F..%2Fetc%2Fpasswd` — Flask decodes to `../../etc/passwd` → `Path("/") / "../../etc/passwd"` resolves to `/etc/passwd`.
**Why it happens:** String prefix matching on `note_path` is bypassed by URL encoding or `../` sequences.
**How to avoid:** Always use `Path(...).resolve()` (which normalizes `..` and symlinks) and check `is_relative_to(brain_root.resolve())` before any file operation.
**Warning signs:** A test like `client.delete("/notes/..%2F..%2Fetc%2Fpasswd")` returning 200.

### Pitfall 4: Delete Button Visible in Edit Mode
**What goes wrong:** User clicks Delete while EasyMDE is open → note deletes without save prompt, losing edits.
**Why it happens:** Toolbar button visibility not managed alongside `enterEditMode()`/`exitEditMode()`.
**How to avoid:** In `enterEditMode()`: `deleteBtn.style.display = 'none'`. In `exitEditMode()`: `deleteBtn.style.display = ''`. Only show in view mode.

### Pitfall 5: `action_items` Table Not Cleaned
**What goes wrong:** After note deletion, `action_items` rows referencing the deleted note's path remain — orphan rows surface in the Actions panel.
**Why it happens:** `forget_person()` doesn't clean `action_items` (it's a per-note concern, not per-person); devs copy that pattern directly.
**How to avoid:** Add `DELETE FROM action_items WHERE note_path=?` to `delete_note()` cascade.
**Warning signs:** Actions panel shows items for a note that no longer exists.

---

## Code Examples

### is_relative_to — Python 3.9+
```python
# Verified: pathlib.Path.is_relative_to() available since Python 3.9
# Project pins Python 3.13 (see MEMORY.md / .python-version)
brain_root = Path(os.environ.get("BRAIN_PATH", "~/SecondBrain")).expanduser().resolve()
p = Path("/some/absolute/path").resolve()
if not p.is_relative_to(brain_root):
    return jsonify({"error": "Forbidden"}), 403
```

### Path.unlink with missing_ok
```python
# Python 3.8+ — safe to use on Python 3.13
abs_path.unlink(missing_ok=True)
# missing_ok=True prevents FileNotFoundError if file already gone (concurrent delete)
```

### FTS5 notes_ad trigger (already in schema — no action needed)
```sql
-- db.py line 30-32: trigger fires automatically on DELETE FROM notes
CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
    INSERT INTO notes_fts(notes_fts, rowid, title, body) VALUES ('delete', old.id, old.title, old.body);
END;
```

### Optimistic sidebar removal (JS)
```javascript
// Remove by data-path attribute — no re-render needed
document.querySelectorAll(`#note-list li[data-path="${pathToDelete}"]`)
    .forEach(el => el.remove());
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|---|---|---|
| String prefix path check (`note_path.startswith(brain_root)`) | `Path.resolve().is_relative_to()` | Symlinks and `../` sequences no longer bypass the guard |
| Manual FTS5 `'delete'` shadow-table ops | `notes_ad` AFTER DELETE trigger | Already in schema; no manual ops needed |

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (pyproject.toml) |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_delete.py tests/test_api.py -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| GUIX-06 | `delete_note()` deletes file from disk | unit | `pytest tests/test_delete.py::test_delete_note_removes_file -x` | Wave 0 |
| GUIX-06 | `delete_note()` removes row from `notes` table | unit | `pytest tests/test_delete.py::test_delete_note_removes_db_row -x` | Wave 0 |
| GUIX-06 | `delete_note()` removes row from `note_embeddings` | unit | `pytest tests/test_delete.py::test_delete_note_removes_embedding -x` | Wave 0 |
| GUIX-06 | `delete_note()` removes rows from `relationships` | unit | `pytest tests/test_delete.py::test_delete_note_removes_relationships -x` | Wave 0 |
| GUIX-06 | `delete_note()` removes rows from `action_items` | unit | `pytest tests/test_delete.py::test_delete_note_removes_action_items -x` | Wave 0 |
| GUIX-06 | `delete_note()` writes audit log entry | unit | `pytest tests/test_delete.py::test_delete_note_audit_log -x` | Wave 0 |
| GUIX-06 | `DELETE /notes/<path>` returns 200 and `{"deleted": true}` | integration | `pytest tests/test_delete.py::test_delete_endpoint_200 -x` | Wave 0 |
| GUIX-06 | `DELETE /notes/<path>` returns 404 for missing note | integration | `pytest tests/test_delete.py::test_delete_endpoint_404 -x` | Wave 0 |
| GUIX-06 | `DELETE /notes/../escape` returns 403 (path traversal) | security | `pytest tests/test_delete.py::test_delete_endpoint_path_traversal_403 -x` | Wave 0 |
| GUIX-06 | `GET /notes/<path>` with traversal returns 403 | security | `pytest tests/test_delete.py::test_get_note_path_traversal_403 -x` | Wave 0 |
| GUIX-06 | `PUT /notes/<path>` with traversal returns 403 | security | `pytest tests/test_delete.py::test_save_note_path_traversal_403 -x` | Wave 0 |
| GUIX-06 | FTS5 index has no row for deleted note after delete | unit | `pytest tests/test_delete.py::test_fts5_clean_after_delete -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_delete.py tests/test_api.py -x -q`
- **Per wave merge:** `uv run pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_delete.py` — all rows above; covers GUIX-06
- [ ] `engine/delete.py` — `delete_note()` utility (if planner chooses separate file over inline)

*(conftest.py and test infrastructure are fully present and sufficient — no new fixtures needed; reuse `brain_root`, `db_conn`, `initialized_db` from conftest.py and the `client`/`tmp_note` fixtures from test_api.py)*

---

## Open Questions

1. **`delete_note()` location: `engine/delete.py` vs inline in `api.py`**
   - What we know: CONTEXT.md marks this as Claude's discretion
   - What's unclear: Whether `forget.py` will be refactored to call `delete_note()` (cross-cutting) in a future phase
   - Recommendation: Separate `engine/delete.py` — this makes it importable by `forget.py` later and keeps `api.py` from growing unboundedly. Low-risk either way.

2. **`action_items` cascade**
   - What we know: `action_items` has a `note_path` FK-style column but no FK constraint; CONTEXT.md does not mention it
   - What's unclear: Whether orphan action items were already accepted as tech debt
   - Recommendation: Include `DELETE FROM action_items WHERE note_path=?` in the cascade — it costs nothing and prevents stale data surfacing in the UI.

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `engine/api.py`, `engine/forget.py`, `engine/watcher.py`, `engine/db.py` — all patterns verified from source
- Direct code inspection: `engine/gui/static/index.html`, `app.js`, `style.css` — modal and toolbar patterns confirmed
- `tests/test_api.py`, `tests/test_forget.py`, `tests/conftest.py` — test patterns and fixture structure confirmed

### Secondary (MEDIUM confidence)
- Python stdlib docs: `pathlib.Path.is_relative_to()` available Python 3.9+; project uses 3.13 (confirmed via MEMORY.md)
- Python stdlib docs: `Path.unlink(missing_ok=True)` available Python 3.8+

### Tertiary (LOW confidence)
- None — all findings verified from source code.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project, verified from imports
- Architecture: HIGH — cascade pattern verified from `forget.py`; modal pattern from `index.html`; suppress pattern from `watcher.py`
- Pitfalls: HIGH — FTS5 trigger behavior verified from `db.py` schema; path traversal pattern is stdlib-documented

**Research date:** 2026-03-16
**Valid until:** 2026-06-16 (stable domain — stdlib + in-project patterns)
