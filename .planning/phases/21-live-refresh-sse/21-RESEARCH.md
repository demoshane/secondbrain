# Phase 21: Live Refresh SSE - Research

**Researched:** 2026-03-16
**Domain:** Flask SSE / watchdog observer / vanilla JS EventSource / pywebview WebKit
**Confidence:** HIGH

## Summary

Phase 21 wires a Server-Sent Events push channel from the Flask sidecar to the browser GUI so that `.md` file changes appear within 2 seconds without any user action. The stack already contains every dependency needed: `watchdog>=6.0` is installed and used in `engine/watcher.py`, `flask>=3.0` supports `stream_with_context` natively, and `EventSource` is a browser-native API fully supported by WebKit/WKWebView.

The main architectural decision is how the watchdog observer thread communicates with the SSE generator threads. A `queue.Queue` per connected client is the canonical thread-safe pattern for Flask SSE without extra dependencies. The observer pushes event dicts onto every registered queue; each SSE generator pulls from its own queue and yields formatted SSE frames. Waitress (the production WSGI server in use) has a known issue with long-lived SSE connections: it does not release the thread when the client disconnects, exhausting the thread pool. The mitigation is periodic heartbeat comments (`": heartbeat\n\n"`) so the generator detects a broken pipe and exits, freeing the thread.

The watchdog observer for `~/SecondBrain` is a sibling of the existing `files/` observer in `engine/watcher.py`. It needs a separate `FileSystemEventHandler` that filters to `.md` files only, debounces rapid changes per-path (≈300ms timer), and pushes `{type, path}` dicts onto all registered client queues. The observer must start inside the Flask/GUI server startup, not as a standalone daemon.

**Primary recommendation:** Use `queue.Queue` per SSE client + a global subscriber list (protected by a `threading.Lock`) + watchdog `Observer` started in `engine/api.py`'s `main()` and also attached when the GUI starts the sidecar inline.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Watch `~/SecondBrain` recursively for `.md` file changes only (not `files/` or binary files)
- Trigger on: created, modified, and deleted events
- Watch all changes regardless of origin — CLI captures, `sb-capture`, direct Finder/editor edits all trigger refresh
- Exclude non-`.md` files (`.db`, `.json`, temp files) from events
- Silent auto-refresh: sidebar list silently reloads when any change event arrives
- No "N new" indicator needed — just update the list in-place
- If the currently open note is modified externally: auto-reload the viewer content
- If the editor has unsaved changes (dirty state) when an external update arrives for the same note: do NOT auto-reload; show conflict banner with Keep/Load choices
- If the currently open note is deleted externally: clear the viewer and show "Note was deleted"
- Use native `EventSource` — browser handles auto-reconnect with exponential backoff
- Show a persistent status dot in the GUI indicating live-refresh connection state (green = connected, grey = disconnected)
- On reconnect after a drop: perform a full notes list refresh to catch any changes missed during the gap
- Each browser tab maintains its own SSE connection (no shared worker)
- Each event carries: `{ type: "created" | "modified" | "deleted", path: "relative/note.md" }`
- SSE stream is designed as general-purpose (notes, actions, intelligence events) even if only note events are wired in this phase — use named event types so future resource types can be added cleanly
- Debounce on the backend: batch rapid file changes within a short window (≈300ms) before firing events
- Notes only in this phase; `files/` subdirectory changes do not produce events

### Claude's Discretion
- Exact debounce implementation (timer per path vs global flush)
- Flask SSE streaming approach (generator + `Response(stream_with_context(...))` or a queue-based approach)
- Status dot placement and exact styling
- How to wire the watchdog observer into the Flask server startup lifecycle

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GUIX-01 | New notes and edits to existing notes are reflected in the GUI without restarting the application (live refresh) | SSE endpoint + watchdog observer + EventSource client pattern fully documented below |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| watchdog | >=6.0 (already installed) | File system events observer | Already used in `engine/watcher.py`; battle-tested on macOS FSEvents |
| flask | >=3.0 (already installed) | SSE generator route via `stream_with_context` | Native streaming support; no extra lib needed |
| queue (stdlib) | Python stdlib | Thread-safe event bus between observer thread and SSE generator threads | Standard pattern for Flask SSE without Redis/pubsub |
| threading (stdlib) | Python stdlib | Lock protecting subscriber list, per-path debounce timers | Already used throughout codebase |
| EventSource (browser) | Native Web API | Client SSE subscription | Supported natively in WebKit/WKWebView on macOS |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| flask.stream_with_context | flask>=3.0 | Keeps Flask request context alive inside a generator | Required for all SSE generator responses |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| queue.Queue per client | Flask-SSE (Redis pubsub) | Flask-SSE requires Redis — unacceptable for a local-first app |
| queue.Queue per client | flask-queue-sse PyPI package | Thin wrapper; no benefit over stdlib queue for single-process use |
| watchdog Observer | polling loop | watchdog uses OS-native FSEvents on macOS — lower latency, lower CPU |

**Installation:** No new dependencies required. All libraries are already in `pyproject.toml`.

---

## Architecture Patterns

### Recommended Project Structure Changes
```
engine/
├── api.py              # Add: /events SSE route, subscriber registry, observer startup
├── watcher.py          # Add: NoteChangeHandler class (sibling of FilesDropHandler)
engine/gui/static/
├── app.js              # Add: EventSource setup, status dot, conflict banner logic
├── index.html          # Add: status dot element
├── style.css           # Add: status dot styles
```

### Pattern 1: Per-Client Queue Subscriber Registry

**What:** A module-level list of `queue.Queue` objects, one per connected SSE client. A `threading.Lock` protects list mutation. The watchdog handler pushes events onto all queues; each SSE generator pops from its own queue.

**When to use:** Single-process Flask with multiple concurrent SSE connections (one per browser tab).

```python
# Source: https://maxhalford.github.io/blog/flask-sse-no-deps/
# Adapted for this codebase

import queue
import threading
from flask import Response, stream_with_context

_subscribers: list[queue.Queue] = []
_subscribers_lock = threading.Lock()

def _subscribe() -> queue.Queue:
    q: queue.Queue = queue.Queue(maxsize=50)
    with _subscribers_lock:
        _subscribers.append(q)
    return q

def _unsubscribe(q: queue.Queue) -> None:
    with _subscribers_lock:
        _subscribers.remove(q)

def _broadcast(event: dict) -> None:
    """Push event onto every subscriber queue. Drop if queue full (slow client)."""
    payload = f"event: note\ndata: {json.dumps(event)}\n\n"
    with _subscribers_lock:
        for q in list(_subscribers):
            try:
                q.put_nowait(payload)
            except queue.Full:
                pass  # slow/disconnected client — drop event
```

### Pattern 2: SSE Generator Route with Heartbeat

**What:** Flask route that subscribes a queue, yields events as SSE frames, sends periodic heartbeat comments to keep the connection alive through Waitress and proxies, and unsubscribes on generator exit.

**When to use:** Every SSE endpoint in this stack.

```python
# Source: Flask docs stream_with_context + Waitress SSE issue #381 mitigation

@app.get("/events")
def event_stream():
    q = _subscribe()

    def generate():
        try:
            while True:
                try:
                    data = q.get(timeout=15)   # 15s heartbeat interval
                    yield data
                except queue.Empty:
                    yield ": heartbeat\n\n"    # keeps Waitress thread alive; client ignores
        except GeneratorExit:
            pass
        finally:
            _unsubscribe(q)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
```

**Critical:** The `finally: _unsubscribe(q)` block is what frees the subscriber when the client disconnects. Without it, queues accumulate indefinitely.

### Pattern 3: NoteChangeHandler (watchdog)

**What:** A `FileSystemEventHandler` subclass that watches `~/SecondBrain` recursively, filters to `.md` files, debounces per-path (300ms timer), and calls `_broadcast()`.

**When to use:** Wired in `api.py` `main()` and in the GUI inline sidecar startup.

```python
# Source: engine/watcher.py existing pattern — extend, don't duplicate

import threading
from pathlib import Path
from watchdog.events import FileSystemEventHandler

DEBOUNCE_MS = 0.3  # seconds

class NoteChangeHandler(FileSystemEventHandler):
    def __init__(self, broadcast_fn):
        self._broadcast = broadcast_fn
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def _is_note(self, path: str) -> bool:
        return path.endswith(".md")

    def _schedule(self, event_type: str, src_path: str) -> None:
        if not self._is_note(src_path):
            return
        with self._lock:
            existing = self._timers.pop(src_path, None)
            if existing:
                existing.cancel()
            t = threading.Timer(
                DEBOUNCE_MS,
                self._fire,
                args=(event_type, src_path),
            )
            self._timers[src_path] = t
        t.start()

    def _fire(self, event_type: str, src_path: str) -> None:
        with self._lock:
            self._timers.pop(src_path, None)
        # Emit relative path (strip brain root prefix)
        brain_root = os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain"))
        try:
            rel = str(Path(src_path).relative_to(brain_root))
        except ValueError:
            rel = src_path
        self._broadcast({"type": event_type, "path": rel})

    def on_created(self, event):
        if not event.is_directory:
            self._schedule("created", event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._schedule("modified", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._schedule("deleted", event.src_path)
```

### Pattern 4: Observer Startup in api.py

**What:** Start the watchdog Observer in `main()` (for `sb-api`) and also provide a `start_note_observer()` helper callable from `engine/gui/__init__.py`'s `_start_sidecar`.

```python
# In engine/api.py main():
from watchdog.observers import Observer

def _start_note_observer() -> Observer:
    brain_root = os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain"))
    handler = NoteChangeHandler(_broadcast)
    obs = Observer()
    obs.schedule(handler, brain_root, recursive=True)
    obs.daemon = True
    obs.start()
    return obs

def main():
    from waitress import serve
    obs = _start_note_observer()
    try:
        serve(app, host="127.0.0.1", port=37491, threads=4)
    finally:
        obs.stop()
        obs.join()
```

For the GUI inline sidecar path (`engine/gui/__init__.py`), the observer must also start because `sb-gui` starts waitress in a daemon thread and never calls `api.main()` directly. Call `_start_note_observer()` from `_start_sidecar()` after the health check passes.

### Pattern 5: EventSource Client (vanilla JS)

**What:** Connect on page load, handle named `note` events, reconnect on error (browser-native), update status dot.

```javascript
// Source: MDN EventSource API + decisions from CONTEXT.md

let evtSource = null;
let sseConnected = false;

function connectSSE() {
    evtSource = new EventSource(`${API}/events`);

    evtSource.onopen = () => {
        sseConnected = true;
        updateStatusDot(true);
    };

    evtSource.addEventListener('note', (e) => {
        const event = JSON.parse(e.data);
        handleNoteEvent(event);
    });

    evtSource.onerror = () => {
        sseConnected = false;
        updateStatusDot(false);
        // EventSource auto-reconnects; on next open we do a full refresh
    };
}

function handleNoteEvent({ type, path }) {
    // Always refresh sidebar
    loadNotes();

    if (!currentPath) return;

    // Normalize paths for comparison
    const absPath = path.startsWith('/') ? path : null;
    const matchesCurrent = currentPath.endsWith(path) || currentPath === path;

    if (!matchesCurrent) return;

    if (type === 'deleted') {
        currentPath = null;
        document.getElementById('viewer').innerHTML = '<em>Note was deleted.</em>';
        return;
    }

    if (type === 'modified') {
        const isDirty = easyMDE !== null;   // editor is open = unsaved changes
        if (isDirty) {
            showConflictBanner();
        } else {
            openNote(currentPath);  // silent reload
        }
    }
}

// On reconnect: EventSource.onopen fires again — trigger full refresh
evtSource.onopen = () => {
    const wasDisconnected = !sseConnected;
    sseConnected = true;
    updateStatusDot(true);
    if (wasDisconnected) loadNotes();
};
```

### Anti-Patterns to Avoid

- **Global single queue (broadcast list without per-client queues):** Causes one slow client to block all others. Use per-client queues.
- **No heartbeat / no timeout on `q.get()`:** Waitress threads stall indefinitely when clients disconnect silently. Always use `q.get(timeout=N)` and yield `": heartbeat\n\n"` on `queue.Empty`.
- **Starting observer in module-level code:** Module is imported in tests; observer would start during `import engine.api`. Gate observer start inside `main()` or an explicit `start_note_observer()` call.
- **Watching the entire `~/SecondBrain` tree without filtering `files/`:** Can flood the event bus. Filter `.md` extension and skip events whose path is under the `files/` subdirectory.
- **Using `on_modified` without debounce:** Text editors write files in multiple rapid `inotify`/FSEvents bursts. Without per-path debounce, the client receives 5-10 events per save. Use per-path timers (≈300ms).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| File system events | Polling loop on `~/SecondBrain` | watchdog Observer (already installed) | OS-native FSEvents on macOS; lower latency, lower CPU; already tested |
| SSE fanout to multiple tabs | Custom threading.Condition broadcast | `queue.Queue` per client + `threading.Lock` | Queue is stdlib, thread-safe by design, handles slow consumers gracefully with `maxsize` |
| Auto-reconnect | Manual `setInterval` reconnect logic | Native `EventSource` | Browser handles exponential backoff natively; no custom code needed |

**Key insight:** The `EventSource` API is intentionally self-healing — do not fight it with custom reconnect timers. Let the browser reconnect; handle the `onopen` event to trigger the post-reconnect full refresh.

---

## Common Pitfalls

### Pitfall 1: Waitress thread pool exhaustion
**What goes wrong:** Each open SSE connection holds a Waitress worker thread. With 4 threads (current config), 4 simultaneous tabs leave no threads for normal API calls.
**Why it happens:** Waitress uses a synchronous thread-per-request model; SSE generators block their thread indefinitely.
**How to avoid:** Increase `threads` from 4 to 8-12 in the `serve()` call, or use a separate Waitress server for `/events`. Given single-user use, increasing to 8 threads is the simplest fix.
**Warning signs:** GUI becomes unresponsive (API calls hang) when multiple tabs are open.

### Pitfall 2: Observer started inside imported module
**What goes wrong:** `import engine.api` in tests starts the watchdog Observer, which immediately starts watching `~/SecondBrain` and spawning threads.
**Why it happens:** Module-level code runs at import time.
**How to avoid:** Gate `_start_note_observer()` inside `main()` only. Tests import `app` (the Flask object) without calling `main()`.
**Warning signs:** Test suite emits watchdog-related warnings; tests fail due to stray threads.

### Pitfall 3: Relative vs absolute path mismatch in JS
**What goes wrong:** The SSE event carries `"people/alice.md"` (relative to brain root) but `currentPath` in `app.js` holds an absolute path like `"/Users/x/SecondBrain/people/alice.md"`. Equality check fails; viewer never auto-reloads.
**Why it happens:** `/notes` API returns absolute paths; SSE events use relative paths.
**How to avoid:** Either (a) make SSE events emit absolute paths, or (b) use `.endsWith(relativePath)` in the JS comparison. Option (b) is safer — no path separator issues.
**Warning signs:** Viewer does not reload on modification even though sidebar updates.

### Pitfall 4: Missing `files/` exclusion
**What goes wrong:** Writes to `~/SecondBrain/files/` (binary attachments) trigger `.md`-filtered events if filenames happen to end in `.md`.
**Why it happens:** `recursive=True` on the observer catches everything under the brain root.
**How to avoid:** In `NoteChangeHandler._is_note()`, also check that the path is not under the `files/` subdirectory: `"files/" not in Path(path).parts`.
**Warning signs:** Spurious refresh events when files are imported.

### Pitfall 5: pywebview SSE compatibility
**What goes wrong:** SSE stream might not work inside pywebview's WKWebView window.
**Why it happens:** The concern was flagged in STATE.md as unconfirmed. Research finding: WKWebView fully supports `EventSource` (WebKit commit history confirms EventSource resource type support). The GUI loads the app via `http://127.0.0.1:37491/ui` — a real HTTP URL, not `file://`. The `CORS` config already allows `http://127.0.0.1:*`. No special pywebview configuration is needed.
**Confidence:** MEDIUM (WebKit supports EventSource confirmed; pywebview-specific documentation did not explicitly confirm, but WKWebView is the underlying engine and the request goes to localhost HTTP, not a file:// origin)
**Recommendation:** Add a minimal SSE proof-of-concept as the first task in Wave 1 to validate before building the full handler. If it fails, fallback is polling every 2 seconds (still meets the 2-second requirement).

### Pitfall 6: Dirty-state detection in JS
**What goes wrong:** The conflict banner logic uses `easyMDE !== null` as the "dirty" signal, but `easyMDE` is set when the editor opens, not when the user types. An open but unmodified editor would incorrectly show the conflict banner.
**Why it happens:** `easyMDE` lifecycle tracks editor presence, not content change.
**How to avoid:** Use EasyMDE's `isCleanDoc()` or track a `isDirty` boolean flag: set it `true` on EasyMDE's `change` event, reset it `false` after a successful save.
**Warning signs:** Conflict banner appears even for notes opened in read mode.

---

## Code Examples

### SSE Frame Format
```
event: note
data: {"type": "modified", "path": "people/alice.md"}

```
Note the double newline (`\n\n`) terminating each event. Named events (`event: note`) allow future event types (`event: action`, `event: intelligence`) on the same stream without client-side confusion.

### Heartbeat Frame Format
```
: heartbeat

```
SSE comments (lines starting with `:`) are ignored by the browser `EventSource` parser. They keep the HTTP connection open through Waitress and any intermediate proxies.

### Status Dot HTML
```html
<!-- Added to index.html topbar -->
<span id="sse-status" class="sse-dot sse-disconnected" title="Live refresh"></span>
```

### Status Dot CSS
```css
.sse-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-left: 8px;
    vertical-align: middle;
}
.sse-dot.sse-connected    { background: #4caf50; }
.sse-dot.sse-disconnected { background: #9e9e9e; }
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Polling (`setInterval` + `fetch`) | SSE (`EventSource`) | Industry shift ~2015; mature since | Sub-second latency; no request overhead; one persistent connection |
| Flask-SSE with Redis | stdlib `queue.Queue` per client | Best practice for single-process apps | No Redis dependency; simpler deployment |

---

## Open Questions

1. **Waitress thread count**
   - What we know: Current config uses `threads=4`. Each SSE connection holds one thread.
   - What's unclear: The user typically has 1-2 tabs open. 4 threads likely sufficient but marginal.
   - Recommendation: Increase to `threads=8` in the `serve()` call as a safe default. No config file change needed.

2. **pywebview SSE validation**
   - What we know: WKWebView supports EventSource natively; request goes to localhost HTTP.
   - What's unclear: No pywebview-specific documentation confirms this in the official docs.
   - Recommendation: Make Wave 1 Task 1 a minimal proof-of-concept (`/events` endpoint yields one `ping` event; JS logs it). Confirm working before building full handler.

3. **Observer in GUI inline sidecar vs sb-api**
   - What we know: `engine/gui/__init__.py` starts waitress in a daemon thread via `_start_sidecar()`, bypassing `api.main()`.
   - What's unclear: Best injection point for the observer.
   - Recommendation: Expose `start_note_observer()` as a public function in `engine/api.py`. Call it from `_start_sidecar()` after the health check passes. Also call it from `api.main()` before `serve()`.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 7.0 |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` testpaths = ["tests"] |
| Quick run command | `uv run pytest tests/test_api_sse.py -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GUIX-01 | `/events` returns SSE stream (200, text/event-stream) | unit | `uv run pytest tests/test_api_sse.py::test_events_endpoint_returns_stream -x` | Wave 0 |
| GUIX-01 | `_broadcast()` delivers event to all subscriber queues | unit | `uv run pytest tests/test_api_sse.py::test_broadcast_delivers_to_all_subscribers -x` | Wave 0 |
| GUIX-01 | `_unsubscribe()` removes queue on client disconnect | unit | `uv run pytest tests/test_api_sse.py::test_unsubscribe_removes_queue -x` | Wave 0 |
| GUIX-01 | `NoteChangeHandler` ignores non-.md files | unit | `uv run pytest tests/test_note_watcher.py::test_non_md_ignored -x` | Wave 0 |
| GUIX-01 | `NoteChangeHandler` debounces rapid modifications | unit | `uv run pytest tests/test_note_watcher.py::test_debounce_suppresses_rapid_events -x` | Wave 0 |
| GUIX-01 | `NoteChangeHandler` fires all three event types | unit | `uv run pytest tests/test_note_watcher.py::test_created_modified_deleted_events -x` | Wave 0 |
| GUIX-01 | SSE event path is relative to brain root | unit | `uv run pytest tests/test_note_watcher.py::test_path_is_relative -x` | Wave 0 |
| GUIX-01 | `files/` subdirectory changes produce no events | unit | `uv run pytest tests/test_note_watcher.py::test_files_dir_excluded -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_api_sse.py tests/test_note_watcher.py -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_api_sse.py` — covers SSE endpoint and broadcast/subscribe logic (GUIX-01)
- [ ] `tests/test_note_watcher.py` — covers `NoteChangeHandler` debounce, filtering, event types (GUIX-01)

---

## Sources

### Primary (HIGH confidence)
- Python stdlib `queue` docs — thread-safe queue, `Queue.put_nowait`, `Queue.get(timeout=N)`
- Python stdlib `threading.Timer` — per-path debounce; already used in `engine/watcher.py`
- Flask docs `stream_with_context` — streaming responses with generator
- watchdog source / existing `engine/watcher.py` — `FileSystemEventHandler` pattern already in codebase

### Secondary (MEDIUM confidence)
- [Max Halford — Flask SSE without dependencies](https://maxhalford.github.io/blog/flask-sse-no-deps/) — per-client queue pattern, verified against Flask docs
- [Waitress issue #381 — SSE pending connections](https://github.com/Pylons/waitress/issues/381) — heartbeat mitigation for Waitress thread exhaustion
- [WebKit commit: EventSource resource type support](https://github.com/WebKit/WebKit/commit/01b796784758982bed20cfe85fdeb6c4f4460d8a) — confirms WKWebView supports EventSource

### Tertiary (LOW confidence)
- Web search results on pywebview + SSE — no pywebview-specific official doc found; inferred from WKWebView being the underlying engine

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies already installed; patterns verified against existing codebase
- Architecture: HIGH — queue-per-client pattern is well-documented and matches Flask + single-process constraints
- Pitfalls: HIGH (Waitress threading, observer import-time startup, path mismatch) / MEDIUM (pywebview SSE — inferred, not officially documented)

**Research date:** 2026-03-16
**Valid until:** 2026-06-16 (stable ecosystem; Flask/watchdog APIs do not change frequently)
