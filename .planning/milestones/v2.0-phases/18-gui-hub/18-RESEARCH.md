# Phase 18: GUI Hub — Research

**Researched:** 2026-03-15
**Domain:** pywebview 5 + Flask HTTP sidecar, JS/Python bridge, Markdown editing, cross-platform desktop
**Confidence:** HIGH (core architecture) / MEDIUM (threading edge cases, Windows WebView2 edge cases)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GUI-01 | `sb-gui` CLI entry point launches desktop window on macOS and Windows | pywebview 5.x + `webview.start()` in `engine/gui.py`; entry point in `pyproject.toml` |
| GUI-02 | Sidebar shows notes browsable by folder/type | `/notes` API already exists; JS sidebar renders grouped by `type` field |
| GUI-03 | Keyword + semantic search from GUI, results in center panel | `/search` API already exists; add `?mode=semantic` param to API |
| GUI-04 | WYSIWYG Markdown editing, atomic save | EasyMDE via CDN (no build step); save via new `PUT /notes/<path>` API endpoint |
| GUI-05 | Backlinks + related notes right panel | New `GET /notes/<path>/meta` API endpoint; search existing backlinks index |
| GUI-06 | Create new notes of any type from GUI | New `POST /notes` API endpoint wrapping `engine.capture`; note type templates |
| GUI-07 | Browse binary files in mirrored subfolder structure | New `GET /files` API endpoint reading `files/` subtree |
| GUI-08 | Move/recategorize files between subfolders | New `POST /files/move` API endpoint wrapping `shutil.move` |
| GUI-09 | Action items panel — view and mark done | `/actions` API exists; add `POST /actions/<id>/done` endpoint |
| GUI-10 | Intelligence panel — recent recap + stale nudges | New `GET /intelligence` endpoint wrapping `engine.intelligence` |
| GUI-11 | Open note in system default editor | `subprocess.Popen(['open', path])` on macOS, `os.startfile(path)` on Windows; or expose via JS bridge |
</phase_requirements>

---

## Summary

Phase 18 builds a cross-platform desktop GUI by wrapping an HTML/JS single-page app inside a native window via **pywebview 5.x**. The architecture decision (locked in v2.0 roadmap) is: `pywebview` window + existing Flask sidecar (`engine/api.py` on port 37491) — GUI calls the HTTP API only, never imports engine modules directly.

The Flask sidecar already exists from Phase 17 with 5 endpoints. Phase 18 must extend the API with ~6 new endpoints (note CRUD, file browsing, file move, metadata/backlinks, intelligence, action-item completion), then build the HTML/JS frontend as static files served by pywebview's built-in bottle server.

The threading model is well-understood: Flask runs in a daemon thread with a `threading.Event` ready-gate; `webview.start()` blocks the main thread and is called only after the API is confirmed healthy. Thread safety is a concern for the JS API bridge (exposed Python functions run in separate threads) but this is avoided entirely by routing all calls through the HTTP API rather than using `js_api`/`expose()`.

**Primary recommendation:** Start Flask sidecar in daemon thread with `threading.Event` gate, poll `/health` before opening window, serve HTML/JS from `engine/gui/static/`, use EasyMDE (CDN, no build step) for WYSIWYG Markdown editing.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pywebview | >=5.0 (latest 5.x) | Native window wrapping WKWebView/WebView2/GTK | Locked decision: PyTauri pre-1.0 ruled out |
| flask | >=3.0 | HTTP sidecar (already in deps) | Already used, provides full API surface |
| waitress | >=3.0 | Production WSGI server (already in deps) | Already used in `sb-api` |
| flask-cors | >=4.0 | CORS for `file://` origin (already in deps) | Already configured in `engine/api.py` |
| pyobjc-core, pyobjc-framework-Cocoa, pyobjc-framework-WebKit | latest | macOS WKWebView binding | Auto-installed by pywebview on macOS |

### Frontend (no build step — all CDN or vendored)

| Asset | Source | Purpose | Why |
|-------|--------|---------|-----|
| EasyMDE | CDN `easymde.min.js` + `easymde.min.css` | WYSIWYG Markdown editor | No build step; CodeMirror-backed; CDN bundle ~150KB |
| marked.js | CDN | Markdown preview rendering (bundled in EasyMDE) | Already dependency of EasyMDE |
| Vanilla JS (ES modules) | Written in-project | Sidebar, panels, fetch calls | No framework needed for this scale |

### Platform Dependencies (runtime, not pip)

| Platform | Renderer | Pre-installed? | Fallback |
|----------|----------|----------------|---------|
| macOS (10.15+) | WKWebView via PyObjC | Yes (pip install pywebview pulls PyObjC) | None needed |
| Windows 11 | WebView2 (Edge Chromium) | Yes — built into OS | N/A |
| Windows 10 (post-2022) | WebView2 | Yes — pushed via Windows Update since mid-2022 | Installer prompt (see Pitfalls) |
| Windows 10 (pre-2021 / managed) | WebView2 | Not guaranteed | Must bundle WebView2 bootstrapper or show error |

**Installation:**
```bash
# Add to pyproject.toml dependencies
pip install pywebview>=5.0
```

macOS PyObjC packages are pulled automatically as pywebview extras. No Qt needed.

---

## Architecture Patterns

### Recommended Project Structure
```
engine/
├── api.py           # existing Flask app (extend with new endpoints)
├── gui.py           # NEW: sb-gui entry point, starts sidecar + webview
└── gui/
    └── static/
        ├── index.html      # single-page shell
        ├── app.js          # ES module, all UI logic
        ├── style.css       # layout: sidebar | center | right panel
        └── vendor/
            ├── easymde.min.js
            └── easymde.min.css
```

### Pattern 1: Flask Sidecar with threading.Event gate

**What:** Flask starts in a daemon thread; main thread polls `/health` before calling `webview.start()`. Prevents window from loading before API is ready.

**When to use:** Every time — this is the only safe startup pattern.

```python
# Source: pywebview.flowrl.com/guide/architecture.html + confirmed pattern
import threading
import time
import urllib.request
import webview
from engine.api import app  # existing Flask app

def _start_flask(ready: threading.Event):
    from waitress import serve
    # Start in background — waitress blocks here
    t = threading.Thread(
        target=serve,
        args=(app,),
        kwargs={"host": "127.0.0.1", "port": 37491, "threads": 4},
        daemon=True,
    )
    t.start()
    # Poll until healthy (max 5s)
    for _ in range(50):
        try:
            urllib.request.urlopen("http://127.0.0.1:37491/health", timeout=0.1)
            ready.set()
            return
        except Exception:
            time.sleep(0.1)

def main():
    ready = threading.Event()
    threading.Thread(target=_start_flask, args=(ready,), daemon=True).start()
    ready.wait(timeout=10)
    window = webview.create_window(
        "Second Brain",
        "http://127.0.0.1:37491/ui",
        width=1280,
        height=800,
        min_size=(900, 600),
    )
    webview.start()
```

### Pattern 2: HTML/JS fetches API via http://127.0.0.1:37491

**What:** All GUI data operations are plain `fetch()` calls to the Flask sidecar. No `js_api`/`expose()` usage — avoids thread-safety complications entirely.

**When to use:** All note reads, searches, saves, action item updates.

```javascript
// Source: standard fetch API — no pywebview bridge needed
async function loadNotes() {
    const res = await fetch('http://127.0.0.1:37491/notes');
    const { notes } = await res.json();
    renderSidebar(notes);
}

async function saveNote(path, content) {
    await fetch(`http://127.0.0.1:37491/notes/${encodeURIComponent(path)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
    });
}
```

### Pattern 3: Open in system default editor (GUI-11)

**What:** Expose a single Python function via `window.expose()` only for OS-level actions that cannot go through HTTP (opening files in external apps). This is the one safe use of the JS bridge.

```python
# Source: pywebview docs + Python stdlib
import subprocess
import os
import sys

def open_in_editor(path: str) -> None:
    """Exposed to JS — runs in separate thread (stateless, safe)."""
    if sys.platform == "darwin":
        subprocess.Popen(["open", path])
    elif sys.platform == "win32":
        os.startfile(path)  # uses Windows shell association
    else:
        subprocess.Popen(["xdg-open", path])

# In main():
window = webview.create_window(..., js_api=None)
window.expose(open_in_editor)
```

Then from JS: `await pywebview.api.open_in_editor(notePath)`

### Pattern 4: New API endpoints needed for Phase 18

The existing API (`engine/api.py`) has 5 endpoints. Phase 18 requires ~7 additions:

| Endpoint | Method | Purpose | GUI Requirement |
|----------|--------|---------|-----------------|
| `/ui` (or serve static) | GET | Serve `index.html` | GUI-01 |
| `/notes` | PUT `/<path>` | Atomic save (write + reindex trigger) | GUI-04 |
| `/notes` | POST | Create new note (wraps `engine.capture`) | GUI-06 |
| `/notes/<path>/meta` | GET | Backlinks + related notes | GUI-05 |
| `/files` | GET | List binary files tree | GUI-07 |
| `/files/move` | POST | Move file between subfolders | GUI-08 |
| `/actions/<id>/done` | POST | Mark action item complete | GUI-09 |
| `/intelligence` | GET | Recap summary + stale nudges | GUI-10 |

### Recommended Three-Panel Layout

```
┌──────────────────────────────────────────────────────────┐
│ [search bar]                              [new note btn]  │
├──────────┬──────────────────────┬────────────────────────┤
│ SIDEBAR  │  CENTER (viewer /    │  RIGHT PANEL           │
│          │  editor)             │  - backlinks           │
│ folders  │                      │  - related notes       │
│ by type  │  EasyMDE or          │  - metadata            │
│          │  rendered Markdown   │  - action items        │
│          │                      │  - intelligence        │
└──────────┴──────────────────────┴────────────────────────┘
```

CSS: three-column flexbox / grid, no external CSS framework needed.

### Anti-Patterns to Avoid

- **Using `js_api` for data operations:** Exposed functions run in separate threads and are not thread-safe. Use the HTTP API for all data calls. Only use `expose()` for the system editor open action (stateless).
- **Importing engine modules directly from `gui.py`:** The locked constraint (C1) is GUI calls `engine/api.py` only. Direct engine imports in the GUI layer are forbidden.
- **Calling `webview.start()` before sidecar is ready:** Race condition — window loads before API responds. Always gate on `threading.Event` + health poll.
- **Using `webview.evaluate_js()` from a non-main thread:** `evaluate_js` must be called from the main thread or via a window event. Use JS `fetch()` polling instead for data sync.
- **Serving HTML from `file://` without CORS adjustment:** pywebview's CORS config in `api.py` already allows `file://*` and `null` origins. Don't remove these.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Markdown editor with preview | Custom textarea + marked.js glue | EasyMDE | Toolbar, shortcuts, split-view, autosave baked in |
| WebView window lifecycle | Manual OS-specific GUI code | `webview.create_window` / `webview.start()` | Platform abstraction over WKWebView/WebView2/GTK |
| WSGI threading | `flask.run(threaded=True)` | waitress (already a dep) | Already used in `sb-api`; production-grade |
| File open via OS | Custom protocol handler | `subprocess.Popen(['open', ...])` / `os.startfile()` | Stdlib; one-liner; correct on all platforms |
| Atomic markdown write | `open(path, 'w')` | `pathlib.Path.write_text()` after temp-file + `os.replace()` | Prevents partial writes on crash |

---

## Common Pitfalls

### Pitfall 1: WebView2 not installed on older Windows 10

**What goes wrong:** `webview.start()` raises an error or shows a blank window on Windows 10 machines that predate the 2022 WebView2 rollout.

**Why it happens:** WebView2 Runtime is auto-deployed on Windows 10 consumer devices since mid-2022 and is part of Windows 11, but enterprise/managed machines may not have it.

**How to avoid:** Catch the webview init error and print a message directing user to download WebView2 bootstrapper from Microsoft. pywebview falls back to MSHTML (old IE engine) on older Windows — this should be blocked explicitly since the GUI requires ES6+.

**Warning signs:** Blank window or JS errors on startup on Windows; test on a clean Windows 10 VM.

### Pitfall 2: `pywebview.api` not ready on `window.onload`

**What goes wrong:** JS code calls `pywebview.api.open_in_editor()` on load but the bridge is not yet initialized, causing a TypeError.

**Why it happens:** pywebview injects the API asynchronously; `window.onload` fires before injection completes.

**How to avoid:** Subscribe to `window.pywebviewready` event instead of `window.onload` for any code that uses `pywebview.api`.

```javascript
window.addEventListener('pywebviewready', () => {
    // safe to call pywebview.api here
});
```

**Warning signs:** `TypeError: Cannot read properties of undefined (reading 'open_in_editor')` in console.

### Pitfall 3: GUI and sb-api running simultaneously on port 37491

**What goes wrong:** If user runs both `sb-api` (standalone) and `sb-gui` at the same time, the second process fails to bind the port.

**Why it happens:** Both `engine/api.py:main()` and `engine/gui.py:_start_flask()` try to bind 127.0.0.1:37491.

**How to avoid:** In `gui.py`, before starting Flask, check if port 37491 is already listening (try a socket connect). If yes, skip starting Flask and just open the webview window pointing at the already-running sidecar.

### Pitfall 4: macOS PyObjC version mismatch with Python 3.13

**What goes wrong:** `pip install pywebview` pulls PyObjC but the installed version may not have wheels for Python 3.13 on Intel Mac.

**Why it happens:** PyObjC binary wheels trail Python minor version releases by weeks/months.

**How to avoid:** Test `pip install pywebview` on the exact Python 3.13 Intel build before planning. If PyObjC wheels are absent, pin to the last working version. Add this to Wave 0 verification.

**Warning signs:** `No matching distribution found for pyobjc-framework-WebKit` during install.

### Pitfall 5: `waitress` in daemon thread may not flush before process exit

**What goes wrong:** On window close, Python exits immediately (daemon thread dies) before waitress can clean up, causing occasional "address already in use" errors on restart.

**Why it happens:** Daemon threads are killed without cleanup on main thread exit.

**How to avoid:** In the webview `closing` event handler, explicitly signal Flask to stop (or just rely on OS port reclaim after exit). For a desktop app this is acceptable. A 0.5s sleep before `sys.exit()` in the closing handler is sufficient.

---

## Code Examples

### Starting the sidecar + window

```python
# Source: pywebview architecture docs + flask-thread pattern
import threading, time, urllib.request, sys
import webview
from engine.api import app as flask_app
from waitress import serve

API_PORT = 37491
API_URL = f"http://127.0.0.1:{API_PORT}"

def _start_sidecar(ready: threading.Event) -> None:
    t = threading.Thread(
        target=serve,
        args=(flask_app,),
        kwargs={"host": "127.0.0.1", "port": API_PORT, "threads": 4},
        daemon=True,
    )
    t.start()
    for _ in range(100):  # 10 seconds max
        try:
            urllib.request.urlopen(f"{API_URL}/health", timeout=0.1)
            ready.set()
            return
        except Exception:
            time.sleep(0.1)

def main() -> None:
    ready = threading.Event()
    threading.Thread(target=_start_sidecar, args=(ready,), daemon=True).start()
    if not ready.wait(timeout=10):
        print("ERROR: API sidecar did not start in time", file=sys.stderr)
        sys.exit(1)

    from engine.gui_api import open_in_editor  # stateless OS helper
    window = webview.create_window(
        "Second Brain",
        f"{API_URL}/ui",
        width=1280, height=800, min_size=(900, 600),
    )
    window.expose(open_in_editor)
    webview.start()
```

### Serving the HTML shell from Flask

```python
# Add to engine/api.py
from pathlib import Path

STATIC_DIR = Path(__file__).parent / "gui" / "static"

@app.get("/ui")
def gui_shell():
    return (STATIC_DIR / "index.html").read_text()

@app.get("/ui/<path:filename>")
def gui_static(filename):
    return flask.send_from_directory(str(STATIC_DIR), filename)
```

### Atomic note save (new PUT endpoint)

```python
# Source: standard atomic write pattern
import os, tempfile
from pathlib import Path
from flask import request, jsonify

@app.put("/notes/<path:note_path>")
def save_note(note_path):
    p = Path(note_path) if note_path.startswith("/") else Path("/") / note_path
    body = request.get_json(force=True) or {}
    content = body.get("content", "")
    # Atomic: write to temp, then replace
    dir_ = p.parent
    with tempfile.NamedTemporaryFile("w", dir=dir_, delete=False, suffix=".tmp", encoding="utf-8") as f:
        f.write(content)
        tmp = f.name
    os.replace(tmp, p)
    return jsonify({"saved": True, "path": str(p)})
```

### EasyMDE initialization (no build step)

```html
<!-- Source: easymde CDN pattern — github.com/Ionaru/easy-markdown-editor -->
<link rel="stylesheet" href="vendor/easymde.min.css">
<script src="vendor/easymde.min.js"></script>
<script>
let editor;
function initEditor(content, onSave) {
    editor = new EasyMDE({
        element: document.getElementById('editor'),
        initialValue: content,
        autosave: { enabled: false },   // manual save on Ctrl+S / button
        spellChecker: false,
        toolbar: ['bold','italic','heading','|','preview','side-by-side','fullscreen'],
    });
    document.addEventListener('keydown', e => {
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            onSave(editor.value());
        }
    });
}
</script>
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pywebview `js_api` for all Python calls | HTTP API + `expose()` only for OS actions | pywebview 3+ | Thread-safe, testable, reuses existing Flask sidecar |
| pywebview CEF on Windows | WebView2 (Edge Chromium) | pywebview 4 | WebView2 ships with Windows; no 150MB CEF bundle |
| pywebview `evaluate_js` returns synchronously | `evaluate_js(code, callback)` for promises | pywebview 3.7 | Avoids blocking main thread |
| Tauri (Python via PyTauri) | pywebview 5 | PyTauri v0.8 (pre-1.0, Feb 2026) | PyTauri not production-ready; revisit at 1.0 |
| SimpleMDE | EasyMDE (maintained fork) | 2019 | SimpleMDE unmaintained; EasyMDE has active releases |

**Deprecated/outdated:**
- `pywebview` CEF backend on Windows: use WebView2 (default since pywebview 4)
- `SimpleMDE`: replaced by EasyMDE (same API, maintained)
- Passing Flask app object directly to `create_window` URL: works but skips health-gate pattern; use thread + health poll instead

---

## Open Questions

1. **PyObjC wheel availability for Python 3.13 on Intel Mac**
   - What we know: pywebview pulls pyobjc-framework-WebKit as dependency; PyObjC is generally kept current
   - What's unclear: Exact wheel availability for Python 3.13.x on Intel x86_64 as of March 2026
   - Recommendation: Wave 0 task must verify `pip install pywebview` succeeds on the project's pinned Python 3.13; if it fails, pin pywebview to last known-good version

2. **Port conflict between `sb-api` and `sb-gui`**
   - What we know: Both processes want 127.0.0.1:37491
   - What's unclear: Whether the user is likely to run both simultaneously; whether port reuse is acceptable
   - Recommendation: Add port-already-open check in `gui.py` startup; if port is occupied, use the existing sidecar rather than starting a new one

3. **EasyMDE CDN vs. vendored files**
   - What we know: pywebview can load from `file://` or `http://127.0.0.1`; CDN requires internet at runtime
   - What's unclear: Whether the project has internet access requirements at GUI runtime
   - Recommendation: Vendor EasyMDE (copy minified bundle into `engine/gui/static/vendor/`) — brain is local-first, internet should not be required to run the GUI

4. **`sb-gui` on Windows: WebView2 bootstrapper requirement**
   - What we know: Windows 10 pre-2022 managed machines may lack WebView2
   - What's unclear: The project's target Windows version floor
   - Recommendation: Add a graceful error message directing users to install WebView2 Runtime from Microsoft; do not bundle the runtime

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7+ |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_gui.py -x -q` |
| Full suite command | `pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GUI-01 | `sb-gui` entry point is registered in `pyproject.toml` | unit | `pytest tests/test_gui.py::TestEntryPoint -x` | Wave 0 |
| GUI-01 | `engine/gui.py:main()` importable without error | unit | `pytest tests/test_gui.py::TestGuiImport -x` | Wave 0 |
| GUI-02 | `/notes` returns list grouped by type | unit (API) | `pytest tests/test_api.py::TestNotesList -x` | Exists (extend) |
| GUI-03 | `/search?mode=semantic` returns results | unit (API) | `pytest tests/test_api.py::TestSearch -x` | Exists (extend) |
| GUI-04 | `PUT /notes/<path>` saves content atomically | unit (API) | `pytest tests/test_api.py::TestSaveNote -x` | Wave 0 |
| GUI-05 | `GET /notes/<path>/meta` returns backlinks key | unit (API) | `pytest tests/test_api.py::TestNoteMeta -x` | Wave 0 |
| GUI-06 | `POST /notes` creates note and returns path | unit (API) | `pytest tests/test_api.py::TestCreateNote -x` | Wave 0 |
| GUI-07 | `GET /files` returns files tree | unit (API) | `pytest tests/test_api.py::TestFilesList -x` | Wave 0 |
| GUI-08 | `POST /files/move` moves file to new path | unit (API) | `pytest tests/test_api.py::TestFilesMove -x` | Wave 0 |
| GUI-09 | `POST /actions/<id>/done` marks item complete | unit (API) | `pytest tests/test_api.py::TestActionDone -x` | Wave 0 |
| GUI-10 | `GET /intelligence` returns recap + nudges | unit (API) | `pytest tests/test_api.py::TestIntelligence -x` | Wave 0 |
| GUI-11 | `open_in_editor(path)` calls correct OS command | unit | `pytest tests/test_gui.py::TestOpenInEditor -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_gui.py tests/test_api.py -x -q`
- **Per wave merge:** `pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_gui.py` — GUI module import, entry point, `open_in_editor` platform dispatch
- [ ] `engine/gui.py` — stub with `main()` raising `NotImplementedError`
- [ ] `engine/gui/static/index.html` — empty shell (Wave 0 scaffold)
- [ ] New test classes in `tests/test_api.py` — `TestSaveNote`, `TestCreateNote`, `TestNoteMeta`, `TestFilesList`, `TestFilesMove`, `TestActionDone`, `TestIntelligence`
- [ ] pywebview dep: `pip install pywebview>=5.0` — verify wheel availability on Python 3.13 Intel

---

## Sources

### Primary (HIGH confidence)

- [pywebview application architecture docs](https://pywebview.flowrl.com/guide/architecture.html) — threading model, Flask integration pattern
- [pywebview 5.0 release notes](https://pywebview.flowrl.com/blog/pywebview5.html) — settings dict, Android support, DOM API
- [pywebview JS-Python bridge guide](https://pywebview.flowrl.com/guide/interdomain) — `expose()`, `js_api`, thread safety warning
- [pywebview installation guide](https://pywebview.flowrl.com/guide/installation.html) — PyObjC requirements, WebView2 requirement
- [EasyMDE GitHub](https://github.com/Ionaru/easy-markdown-editor) — CDN usage, API, CodeMirror backbone
- `engine/api.py` (project file) — existing 5 endpoints, CORS config, Flask app instance
- `pyproject.toml` (project file) — existing deps (flask, waitress, flask-cors already present)

### Secondary (MEDIUM confidence)

- [WebView2 distribution docs — Microsoft Learn](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution) — Windows 10/11 deployment status
- [WebView2 Windows 10 consumer rollout — Microsoft Edge Blog](https://blogs.windows.com/msedgedev/2022/06/27/delivering-the-microsoft-edge-webview2-runtime-to-windows-10-consumers/) — rollout timeline
- [pywebview Flask sidecar Medium article (Feb 2025)](https://medium.com/@nohkachi/how-to-build-a-python-desktop-app-with-pywebview-and-flask-73025115e061) — startup sequencing pattern with `ready_event`
- `.planning/STATE.md` decisions table — locked choice: pywebview over PyTauri; GUI calls API only (C1)

### Tertiary (LOW confidence)

- WebSearch: pywebview 5.4 specific changelog details — could not independently verify exact 5.4 feature set; use official changelog at `pywebview.flowrl.com/changelog`

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pywebview locked decision; Flask/waitress already in deps; EasyMDE CDN verified on official GitHub
- Architecture: HIGH — Flask-thread + health-gate is a well-documented, verified pattern
- Threading model: HIGH — official docs explicitly state `expose()` runs in separate threads; HTTP-API-only approach sidesteps this
- Windows WebView2 edge case: MEDIUM — deployment data from 2022; current 2026 coverage on Windows 10 unverified
- PyObjC on Python 3.13 Intel: MEDIUM — wheel availability unconfirmed for exact platform; must verify in Wave 0

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (pywebview stable; 30 days safe)
