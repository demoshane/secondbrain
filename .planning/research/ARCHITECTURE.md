# Architecture Research

**Domain:** Local-first desktop knowledge app — v3.0 GUI Overhaul and Engine Polish
**Researched:** 2026-03-16
**Confidence:** HIGH (based on direct code inspection of existing system)

---

## System Overview

### Existing v2.0 Architecture (unchanged baseline)

```
┌─────────────────────────────────────────────────────────────────┐
│                      pywebview OS window                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  engine/gui/static/  (HTML + vanilla JS, served by Flask) │  │
│  │  index.html  app.js  style.css  vendor/easymde.*          │  │
│  │                                                           │  │
│  │  All calls → fetch('http://127.0.0.1:37491/...')          │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP (loopback only)
┌──────────────────────────▼──────────────────────────────────────┐
│                  engine/api.py  (Flask + waitress)               │
│  /health  /notes  /search  /actions  /intelligence  /files      │
│  /ui  /ui/<filename>  — static file server for GUI assets        │
│                                                                  │
│  Imports only: engine/db  engine/search  engine/intelligence     │
└──────┬───────────────┬──────────────────┬───────────────────────┘
       │               │                  │
┌──────▼──────┐  ┌─────▼──────┐  ┌───────▼───────────────────────┐
│ engine/db   │  │engine/      │  │ engine/intelligence.py         │
│ get_conn    │  │search.py    │  │ engine/health.py               │
│ init_schema │  │search_notes │  │ engine/capture.py              │
│             │  │search_hybrid│  │ engine/embeddings.py           │
└──────┬──────┘  └─────────────┘  └───────────────────────────────┘
       │
┌──────▼────────────────────────────────────────────────────────┐
│            ~/SecondBrain/.meta/brain.db  (SQLite)             │
│  notes  notes_fts(FTS5)  note_embeddings(sqlite-vec)          │
│  relationships  action_items  audit_log                        │
└───────────────────────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────────────┐
│                ~/SecondBrain/  (filesystem)                   │
│  meetings/  people/  coding/  strategy/  projects/           │
│  personal/  ideas/  files/  .meta/                           │
└──────────────────────────────────────────────────────────────┘
```

### Key constraint

The GUI-to-engine boundary is hard: the pywebview HTML page calls Flask endpoints only — it never imports Python modules. Every new feature the GUI needs must be backed by a new or extended Flask route in `engine/api.py`.

---

## Component Responsibilities

| Component | Responsibility | v3.0 Status |
|-----------|---------------|-------------|
| `engine/api.py` | HTTP surface — only entry point from GUI | Modified — new routes added |
| `engine/gui/static/app.js` | All GUI logic — calls API only | Modified — SSE, tag edit, file upload, health panel |
| `engine/gui/static/index.html` | Shell — loads app.js and EasyMDE | Modified — new DOM elements |
| `engine/gui/static/style.css` | Layout and scroll behaviour | Modified — scroll fix, collapsible sidebar |
| `engine/search.py` | FTS5 BM25, semantic, hybrid RRF | Modified — tag filter param, optional RRF k tuning |
| `engine/health.py` | System component checks (CLI `sb-health`) | Modified — new brain data quality checks |
| `engine/intelligence.py` | Recap, actions, stale nudges | Modified — expose recap trigger function |
| `engine/capture.py` | Single-note atomic capture | Modified — `batch_capture()` added |
| `engine/db.py` | SQLite connection + schema | Possibly modified — tags column index |

No new top-level Python files are required. All changes land in existing modules.

---

## Recommended Project Structure

Changes annotated per file. No new directories.

```
engine/
├── api.py              # Add: GET /events (SSE), POST /internal/notify,
│                       #      DELETE /notes/<path>, PATCH /notes/<path>/tags,
│                       #      POST /files/upload, POST /recap/trigger,
│                       #      GET /health/brain, POST /batch-capture
├── search.py           # Modify: add tag_filter param to search_notes();
│                       #         optionally tune RRF k constant
├── health.py           # Add: BRAIN_CHECKS group (orphans, broken links, dupes)
│                       #      and compute_brain_score()
├── capture.py          # Add: batch_capture(items) wrapping existing capture_note()
├── intelligence.py     # Add: expose generate_recap() as a callable function
│                       #      (currently only triggered by launchd / CLI)
└── gui/
    └── static/
        ├── index.html  # Add: tag editor widget, file input, recap button,
        │               #      health dashboard section, delete button
        ├── app.js      # Add: EventSource subscriber, tag edit handlers,
        │               #      file upload, health panel, sidebar collapse,
        │               #      frontmatter strip before marked.parse()
        └── style.css   # Add: overflow-y: auto on #viewer and #center,
                        #      collapsible sidebar CSS
```

---

## Architectural Patterns

### Pattern 1: Server-Sent Events for Live Refresh (GUIX-01, GUIX-02)

**What:** Flask streams `text/event-stream` on `GET /events`. An in-process `queue.SimpleQueue` acts as the event bus. Any write operation (save, create, delete, batch-capture) posts to the queue. The JS `EventSource` subscriber calls `loadNotes()` on `notes_changed` events.

**Why SSE over WebSocket:** SSE is one-directional (server to client) which is all that is needed. It works over standard WSGI with no new dependencies. WebSocket requires `flask-socketio` + gevent/eventlet, which breaks waitress and monkey-patches the stdlib — unacceptable overhead.

**Why SSE over polling:** Polling floods the DB constantly and causes sidebar flicker. SSE pushes exactly when something changes.

**waitress threading note:** The existing `waitress serve(..., threads=4)` keeps one thread occupied per open SSE connection. With one GUI window (single user) this is acceptable. If needed, bump to `threads=8`.

**Implementation sketch:**

```python
# engine/api.py — additions
import queue, json as _json
_event_bus: queue.SimpleQueue = queue.SimpleQueue()

def _notify(event_type: str = "notes_changed") -> None:
    _event_bus.put(_json.dumps({"type": event_type}))

@app.get("/events")
def sse_stream():
    def generate():
        while True:
            msg = _event_bus.get()   # blocks; releases thread only on event
            yield f"data: {msg}\n\n"
    return app.response_class(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@app.post("/internal/notify")
def internal_notify():
    _notify()
    return jsonify({"ok": True})
```

```javascript
// app.js — addition
const evtSource = new EventSource(`${API}/events`);
evtSource.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === 'notes_changed') loadNotes();
};
```

`_notify()` is called at the end of: `save_note()`, `create_note()`, `delete_note()` (new), `patch_tags()` (new), `batch_capture_endpoint()` (new), `files_upload()` (new).

**Watcher process bridge:** `sb-watch` runs as a separate launchd process and cannot call `_notify()` directly. After detecting a new file and triggering reindex, the watcher posts to `POST /internal/notify` over loopback. No authentication needed — loopback-only binding.

### Pattern 2: Client-Side Markdown Rendering (GUIX-03)

**What:** `marked.js` is already present globally — it is bundled inside `vendor/easymde.min.js`. The `renderMarkdown()` function in `app.js` already calls `marked.parse(md)`. The feature is architecturally complete.

**The bug:** Raw note content includes a YAML frontmatter block (`---\ntype: ...\n---`). When passed directly to `marked.parse()`, YAML frontmatter renders as a table or raw text at the top of the note. The fix is a one-line strip before calling `marked.parse()`.

**Fix location:** `app.js` `renderMarkdown()` — strip frontmatter before render. No API change. No new dependency.

```javascript
function stripFrontmatter(md) {
    return md.replace(/^---[\s\S]*?---\n?/, '');
}
function renderMarkdown(md) {
    const viewer = document.getElementById('viewer');
    viewer.innerHTML = typeof marked !== 'undefined'
        ? marked.parse(stripFrontmatter(md))
        : stripFrontmatter(md);
    // ... rest unchanged
}
```

### Pattern 3: Tag Editing via PATCH endpoint (GNAV-02, GNAV-03)

**What:** New `PATCH /notes/<path>/tags` accepts `{"tags": ["a","b"]}`. The handler parses YAML frontmatter from the file, rewrites the `tags:` field, and does an atomic `os.replace(tmp, p)` write — same pattern as `save_note()`. It also updates `notes.tags` in SQLite and calls `_notify()`.

**Why PATCH, not PUT:** `PUT /notes/<path>` handles full content replacement. A `PATCH` on the `/tags` sub-resource keeps concerns separated: the GUI does not need to round-trip the entire note body to update a tag. The body content is untouched.

**Frontmatter rewriting:** Use a simple regex rewrite on the `tags:` line rather than a full YAML roundtrip. The frontmatter format is fixed (written by `create_note()`) and does not require a YAML library for this narrow operation.

**Database schema:** The `notes` table currently selects `path, title, type, created_at` in `api.py`. Whether a `tags` column exists needs confirmation against `engine/db.py init_schema`. If missing, add it as a non-breaking `ALTER TABLE` (SQLite allows adding columns with a default value).

**Tag filter in search:** Extend `search_notes()` in `engine/search.py` with an optional `tag_filter` param. If tags are stored as a comma-joined string, use `WHERE tags LIKE '%' || ? || '%'`. If stored as JSON array, use `json_each`. The `/search` endpoint passes the tag through from request body.

### Pattern 4: Brain Health Dashboard (ENGL-04, ENGL-05)

**What:** New `GET /health/brain` endpoint runs a group of data-quality checks against the DB and filesystem and returns structured JSON.

**Where the checks live:** Add a second group to the existing `engine/health.py`. The existing `CHECKS` list covers system components (launchd, Ollama, MCP binary). The new `BRAIN_CHECKS` list covers data quality. `main()` uses `CHECKS` as before; `api.py` imports `BRAIN_CHECKS` for the `/health/brain` route.

```python
# engine/health.py — additions
def check_orphan_notes() -> dict:
    """Notes with no backlinks and no outgoing relationships."""
    ...

def check_broken_links() -> dict:
    """Relationships table entries where target path does not exist on disk."""
    ...

def check_duplicate_titles() -> dict:
    """Notes table entries sharing the same title (case-insensitive)."""
    ...

def compute_brain_score(results: list[dict]) -> int:
    fails = sum(1 for r in results if r["status"] == "fail")
    warns = sum(1 for r in results if r["status"] == "warn")
    return max(0, 100 - (fails * 10) - (warns * 3))

BRAIN_CHECKS = [check_orphan_notes, check_broken_links, check_duplicate_titles]
```

```python
# engine/api.py — new route
from engine.health import BRAIN_CHECKS, compute_brain_score

@app.get("/health/brain")
def brain_health():
    results = []
    for fn in BRAIN_CHECKS:
        try:
            results.append(fn())
        except Exception as exc:
            results.append({"label": fn.__name__, "status": "fail", "detail": str(exc)})
    return jsonify({"score": compute_brain_score(results), "checks": results})
```

### Pattern 5: Batch Capture (ENGL-01)

**What:** New `POST /batch-capture` accepts `{"items": [{"title":..., "type":..., "body":...}]}`. The handler calls a new `batch_capture(items)` function in `engine/capture.py` that loops over items, reusing the existing single-item `capture_note()` logic. All items are captured inside a single SQLite transaction. Returns `{"captured": N, "paths": [...]}`.

**No duplication:** `batch_capture()` wraps `capture_note()` — it does not copy its logic. The single-item code path is unchanged.

```python
# engine/capture.py — addition
def batch_capture(items: list[dict]) -> list[str]:
    """Capture multiple notes in a single transaction. Returns list of paths."""
    paths = []
    conn = get_connection()
    try:
        conn.execute("BEGIN")
        for item in items:
            path = capture_note(item["title"], item["type"], item.get("body",""), conn=conn)
            paths.append(path)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return paths
```

### Pattern 6: File Upload from GUI (GUIF-01)

**What:** New `POST /files/upload` accepts `multipart/form-data` with a `file` field. It saves the uploaded file to `~/SecondBrain/files/` using `werkzeug.utils.secure_filename`, creates a companion markdown index note (type `file`, title = filename), and returns `{"file_path": ..., "note_path": ...}`.

**Why a separate endpoint:** The existing `POST /files/move` moves files already on disk. A browser `<input type="file">` sends a `multipart/form-data` POST — that requires a distinct endpoint. Flask's `request.files` handles the upload; werkzeug's `secure_filename` prevents path traversal.

**JS side:** A hidden `<input type="file" id="file-upload-input">` in the toolbar. On `change`, build a `FormData` object and POST to `/files/upload`. On success, call `loadNotes()` (which also triggers `_notify()` server-side).

---

## New vs Modified — Explicit Mapping

| Requirement | New or Modified | Component | What Changes |
|-------------|----------------|-----------|--------------|
| GUIX-01 Live refresh | New | `engine/api.py` | `GET /events` (SSE), `POST /internal/notify`, `_notify()` helper, call `_notify()` in all write routes |
| GUIX-01 Live refresh | New | `app.js` | `EventSource` subscriber, call `loadNotes()` on event |
| GUIX-02 Title edits reflected | Bug fix | `engine/api.py` `save_note()` | Parse new frontmatter after write; `UPDATE notes SET title=?, updated_at=? WHERE path=?` |
| GUIX-03 Markdown rendering | Bug fix | `app.js` `renderMarkdown()` | Strip YAML frontmatter before `marked.parse()` |
| GUIX-04 Mouse scroll | CSS fix | `style.css` | `overflow-y: auto` on `#viewer` and `#center` |
| GUIX-05 Backlinks fix | Bug fix | `engine/api.py` `note_meta()` | Replace fragile `LIKE` heuristic with `relationships` table query |
| GUIX-06 Delete note | New | `engine/api.py` | `DELETE /notes/<path>` with cascade: file, notes row, FTS5, note_embeddings, relationships, audit_log |
| GUIX-06 Delete note | Modified | `app.js`, `index.html` | Delete button in viewer toolbar + confirm dialog |
| GNAV-01 Sidebar collapse | Modified | `app.js` `renderSidebar()`, `style.css` | Type-group headers toggle visibility; CSS for collapsed/expanded state |
| GNAV-02 Tag editing | New | `engine/api.py` | `PATCH /notes/<path>/tags` — atomic frontmatter rewrite + DB update |
| GNAV-02 Tag editing | Modified | `app.js`, `index.html` | Tag editor widget in viewer toolbar (inline chips + input) |
| GNAV-03 Tag filter | Modified | `engine/api.py` `search()` | Accept optional `tag` param, pass to `search_notes()` |
| GNAV-03 Tag filter | Modified | `engine/search.py` `search_notes()` | Add `tag_filter` param, extend SQL WHERE clause |
| GNAV-03 Tag filter | Modified | `app.js`, `index.html` | Tag filter dropdown above note list in sidebar |
| GUIF-01 File capture | New | `engine/api.py` | `POST /files/upload` (multipart) using `werkzeug.utils.secure_filename` |
| GUIF-01 File capture | Modified | `index.html`, `app.js` | Hidden `<input type="file">`, `FormData` upload handler |
| GUIF-02 On-demand recap | New | `engine/api.py` | `POST /recap/trigger` — calls `intelligence.generate_recap()`, returns markdown string |
| GUIF-02 On-demand recap | Modified | `engine/intelligence.py` | Expose `generate_recap()` as a callable (currently only CLI/launchd triggered) |
| GUIF-02 On-demand recap | Modified | `index.html`, `app.js` | "Run Recap" button in intelligence panel; display result in `#recap-content` |
| ENGL-01 Batch capture | New | `engine/capture.py` | `batch_capture(items)` wrapping `capture_note()` in single transaction |
| ENGL-01 Batch capture | New | `engine/api.py` | `POST /batch-capture` endpoint |
| ENGL-02 Search quality | Modified | `engine/search.py` `_rrf_merge()` | Tune `k` constant (default 60); optionally add field-weighted BM25 column weights |
| ENGL-03 AI quality | Modified | `engine/intelligence.py` | Improve recap and action extraction prompts — no API surface change |
| ENGL-04 Brain health data | Modified | `engine/health.py` | Add `BRAIN_CHECKS`: `check_orphan_notes`, `check_broken_links`, `check_duplicate_titles` |
| ENGL-04 Brain health data | New | `engine/api.py` | `GET /health/brain` endpoint |
| ENGL-05 Health score | Modified | `engine/health.py` | Add `compute_brain_score(results)` |
| ENGL-05 Health score | Modified | `index.html`, `app.js` | Health dashboard section in right panel; score badge |

---

## Data Flow

### Live Refresh Flow

```
[Any write in GUI]
    ↓
PUT /notes/<path>  →  save_note()  →  os.replace(tmp, p)  →  UPDATE notes
    ↓
_notify()  →  _event_bus.put('{"type":"notes_changed"}')
    ↓
GET /events (SSE long-poll, open)  →  yield data frame
    ↓
EventSource.onmessage  →  loadNotes()  →  GET /notes  →  renderSidebar()
```

```
[sb-watch daemon detects new file on disk]
    ↓
POST /internal/notify  (loopback, no auth — localhost only)
    ↓
_notify()  →  _event_bus.put(...)  →  (same SSE path as above)
```

### Tag Edit Flow

```
[User edits tags in tag editor widget]
    ↓
PATCH /notes/<path>/tags  {"tags": ["a","b"]}
    ↓
Read file  →  regex-rewrite tags: line in frontmatter
    ↓
atomic os.replace(tmp, p)
    ↓
UPDATE notes SET tags=? WHERE path=?
    ↓
_notify()
    ↓
{"saved": true, "tags": ["a","b"]}
```

### Note Deletion Flow (GUIX-06)

```
[User clicks Delete + confirms]
    ↓
DELETE /notes/<path>
    ↓
1. p.unlink()                                          (filesystem)
2. DELETE FROM notes WHERE path=?                      (index)
3. DELETE FROM notes_fts WHERE rowid = note.id         (FTS5)
4. DELETE FROM note_embeddings WHERE note_path=?       (vectors)
5. DELETE FROM relationships WHERE source=? OR target=? (graph)
6. INSERT INTO audit_log (event_type='delete', ...)    (audit)
    ↓
_notify()
    ↓
{"deleted": true}
```

### Brain Health Flow

```
[User opens health dashboard OR health panel auto-loads]
    ↓
GET /health/brain
    ↓
engine/health.py: BRAIN_CHECKS run against DB + filesystem
    orphan check: notes with no relationships rows
    broken link check: relationships.target paths not on disk
    duplicate check: notes with identical title (case-insensitive)
    ↓
compute_brain_score(results)  →  0–100 integer
    ↓
{"score": 87, "checks": [...]}  →  GUI renders score badge + issue lists
```

### Search with Tag Filter Flow

```
[User selects tag filter in sidebar]
    ↓
POST /search  {"query": "...", "tag": "meetings"}
    ↓
search_notes(conn, query, tag_filter="meetings")
    ↓
FTS5 SQL + AND n.tags LIKE '%meetings%'
    ↓
Return filtered, BM25-ranked results
```

### Batch Capture Flow

```
[External trigger or GUI batch action]
    ↓
POST /batch-capture  {"items": [{...}, {...}]}
    ↓
engine/capture.py: batch_capture(items)
    conn.execute("BEGIN")
    for item in items: capture_note(...)   (reuses existing logic)
    conn.commit()
    ↓
_notify()  (once, after all items written)
    ↓
{"captured": N, "paths": [...]}
```

---

## Internal Boundaries

| Boundary | Communication | Constraint |
|----------|---------------|-----------|
| GUI JS to Flask | HTTP fetch to 127.0.0.1:37491 | Hard — GUI never imports Python |
| SSE stream to app.js | `EventSource` long-poll | One connection per GUI window; fine for single user |
| `sb-watch` daemon to Flask | `POST /internal/notify` over loopback | Separate process; must not import `api.py` |
| `api.py` to engine modules | Direct Python import | Only `engine.db`, `engine.search`, `engine.intelligence`, `engine.health`, `engine.capture` |
| `health.py` system checks vs brain checks | Same module, two groups: `CHECKS` and `BRAIN_CHECKS` | CLI `main()` uses `CHECKS`; `/health/brain` route uses `BRAIN_CHECKS` |
| `capture.py` single vs batch | `batch_capture()` calls `capture_note()` — no logic duplication | Single-item path unchanged |

---

## Anti-Patterns

### Anti-Pattern 1: WebSocket for live refresh

**What people do:** Add `flask-socketio` + gevent or eventlet for real-time push.
**Why it's wrong:** Requires monkey-patching the stdlib (gevent breaks waitress), adds two heavy dependencies, and is bi-directional where only one direction is needed.
**Do this instead:** Flask `text/event-stream` + `EventSource`. One `queue.SimpleQueue` in-process. Zero new dependencies.

### Anti-Pattern 2: Server-side markdown rendering

**What people do:** Add `mistune` or `markdown` Python package, render HTML in Flask, return an HTML string from the note endpoint.
**Why it's wrong:** `marked.js` is already vendored inside `easymde.min.js` and available globally. Adding a server-side renderer duplicates the dependency, adds a round-trip, and makes the viewer feel slower.
**Do this instead:** Strip frontmatter in `renderMarkdown()` then call `marked.parse()`. The wiring is already there — only the strip step is missing.

### Anti-Pattern 3: Polling for live refresh

**What people do:** `setInterval(() => loadNotes(), 5000)` — reload the full note list every N seconds.
**Why it's wrong:** Constant DB reads, visible sidebar flicker on every interval, CPU burn when nothing changed.
**Do this instead:** SSE push — server signals exactly when something changes; JS reloads only then.

### Anti-Pattern 4: Overloading PUT /notes for tag updates

**What people do:** Send the full note content back via `PUT /notes/<path>` with updated frontmatter tags embedded.
**Why it's wrong:** GUI must hold the full body in memory to re-serialize frontmatter, risks overwriting concurrent edits, and makes tag-only changes unnecessarily heavy.
**Do this instead:** `PATCH /notes/<path>/tags` — server owns frontmatter rewriting, body is untouched.

### Anti-Pattern 5: Direct DB access from the watcher process

**What people do:** Have `sb-watch` open `brain.db` directly to update the index after detecting a file change.
**Why it's wrong:** Two concurrent writers (Flask + watcher) create SQLite locking contention even with WAL mode, especially during batch reindex.
**Do this instead:** Watcher triggers reindex via CLI (`sb-reindex`), then posts to `POST /internal/notify`. Flask owns the DB connection lifecycle.

### Anti-Pattern 6: Separate health module for brain data checks

**What people do:** Create `engine/brain_health.py` as a new module.
**Why it's wrong:** `engine/health.py` already exists and has the check helper pattern (`_ok`, `_warn`, `_fail`). A second module creates an awkward split with no benefit — the existing module already separates `CHECKS` (system) from `BRAIN_CHECKS` (data quality) by list name.
**Do this instead:** Add `BRAIN_CHECKS` group to `engine/health.py`. Import only what is needed in each consumer.

---

## Build Order

Dependencies drive the sequence. The SSE infrastructure (step 3) is the backbone — once in place, every subsequent write endpoint can call `_notify()` for free.

| Order | Feature Group | Requirements | Key Dependency |
|-------|--------------|--------------|---------------|
| 1 | GUIX-03 markdown + GUIX-04 scroll | JS one-liner fix + CSS two-liner | None — pure frontend |
| 2 | GUIX-05 backlink fix + GUIX-02 title sync | Query fix in `note_meta()`; UPDATE in `save_note()` | None |
| 3 | GUIX-01 Live refresh (SSE) | `_event_bus`, `GET /events`, `POST /internal/notify`, `EventSource` in JS | Steps 1-2 complete so refresh is visually coherent |
| 4 | GUIX-06 Note deletion | `DELETE /notes/<path>` with cascade | Step 3 (SSE to remove from sidebar) |
| 5 | GNAV-01 Sidebar collapse | JS/CSS only — no new endpoints | Step 3 (collapse state survives refresh) |
| 6 | GNAV-02 Tag editing + GNAV-03 Tag filter | `PATCH /notes/<path>/tags`, extend `search_notes()`, tag filter UI | Steps 3-4 |
| 7 | GUIF-01 File upload | `POST /files/upload`, `<input type="file">` in JS | Step 3 (SSE to surface new note) |
| 8 | GUIF-02 On-demand recap | `POST /recap/trigger`, expose `generate_recap()` | Step 3 (SSE optionally refreshes intelligence panel) |
| 9 | ENGL-04/05 Brain health dashboard | `BRAIN_CHECKS` in `health.py`, `GET /health/brain`, health panel in GUI | None — standalone |
| 10 | ENGL-01 Batch capture | `batch_capture()` in `capture.py`, `POST /batch-capture` | Step 3 (SSE to push results) |
| 11 | ENGL-02 Search quality (RRF tuning) | Tune `_rrf_merge()` k; optionally add BM25 column weights | None — but needs test queries to validate; do last |
| 12 | ENGL-03 AI quality | Prompt engineering in `intelligence.py` | None — iterative; do last |

---

## Scaling Considerations

Single-user local app. Scaling concerns are note volume and latency, not concurrency.

| Concern | Current state | Risk | Mitigation |
|---------|--------------|------|------------|
| SSE thread starvation | waitress 4 threads; SSE holds one | Low — one GUI window | Increase to `threads=8` if needed |
| Brain health queries | Full table scan for orphans/dupes | Low — brain < 10k notes | On-demand only; no continuous indexing |
| Tag filter search | `LIKE '%tag%'` is O(n) | Low — < 10k notes | Acceptable; if tags stored as JSON use `json_each` for correctness |
| Batch capture transaction | Loop in single `BEGIN`/`COMMIT` | Low — typical batch < 100 items | Fine; explicit transaction wrapping the loop |
| Frontmatter regex rewrite | File read + regex + atomic write per tag update | Negligible | No concern |

---

## Sources

- Direct code inspection: `engine/api.py`, `engine/search.py`, `engine/health.py`, `engine/gui/static/app.js`, `engine/gui/static/index.html` — 2026-03-16 (HIGH confidence)
- Flask streaming responses (SSE): https://flask.palletsprojects.com/en/3.1.x/patterns/streaming/ (HIGH confidence — official Flask docs)
- MDN EventSource API: https://developer.mozilla.org/en-US/docs/Web/API/EventSource (HIGH confidence)
- waitress threading model: https://docs.pylonsproject.org/projects/waitress/en/stable/runner.html — `threads=4` confirmed in existing `main()` (HIGH confidence)
- EasyMDE bundles marked.js: confirmed by `vendor/easymde.min.js` presence and existing `marked.parse()` call in `app.js` (HIGH confidence — direct inspection)
- werkzeug `secure_filename`: https://werkzeug.palletsprojects.com/en/3.1.x/utils/#werkzeug.utils.secure_filename (HIGH confidence — official docs)

---

*Architecture research for: Second Brain v3.0 — GUI Overhaul and Engine Polish*
*Researched: 2026-03-16*
