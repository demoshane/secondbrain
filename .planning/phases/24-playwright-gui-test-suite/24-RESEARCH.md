# Phase 24: Playwright GUI Test Suite - Research

**Researched:** 2026-03-16
**Domain:** pytest-playwright, Flask live server, end-to-end browser testing
**Confidence:** HIGH

## Summary

Phase 24 adds a `pytest tests/test_gui.py` suite that spins up the real Flask API (`engine/api.py`) in a background thread and drives it with a headless Chromium browser via pytest-playwright. The suite covers the ten success criteria spanning markdown rendering, scrolling, title sync, SSE live refresh, delete flow, tag editing, tag filtering, collapsible sidebar sections, and the path traversal guard.

The project does not yet have `pytest-playwright` installed. It needs to be added to `pyproject.toml [dev]` along with `playwright` (the browser binaries are installed separately with `playwright install chromium`). The existing `conftest.py` patterns — `monkeypatch.setenv("BRAIN_PATH", ...)`, `tmp_path` brain directory seeding, and the `stub_engine_embeddings` autouse fixture — all apply directly to the GUI test file, since the Flask app reads `BRAIN_PATH` from the environment at request time.

The key architectural decision is how to run the live Flask server. pytest-flask's `live_server` fixture has a documented teardown hang with playwright-pytest (GitHub issue #187 on microsoft/playwright-pytest). The safe, zero-dependency alternative used across the ecosystem is a session-scoped `threading.Thread(daemon=True)` fixture that starts the Flask `app.run()` on a random port. The `base_url` is then injected into Playwright via the pytest-playwright `--base-url` CLI arg or the `base_url` fixture override.

**Primary recommendation:** Use a custom `live_server` fixture (threading.Thread + daemon=True, random port) instead of pytest-flask's live_server. Set `base_url` fixture to point Playwright at that port. Seed the test brain with `tmp_path` + `monkeypatch.setenv("BRAIN_PATH")` using the same pattern as `tmp_note` in `test_api.py`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TEST-01 | Playwright GUI test suite covers all GUI features from phases 20–23 (markdown, scroll, title sync, SSE, delete, tags, collapsible sidebar, path traversal) | All 10 success criteria mapped to specific selectors and API patterns below |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest-playwright | >=0.5.0 | pytest fixtures for page/browser/context; headless Chromium | Official Microsoft plugin; provides `page`, `browser`, `context` fixtures out of box |
| playwright | >=1.40 | Browser automation engine | Playwright Python; installed separately from pytest-playwright |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest (already installed) | >=7.0 | Test runner | Already in dev deps |
| threading (stdlib) | - | Spin up Flask in background thread | Preferred over pytest-flask for playwright due to teardown hang issue |
| pytest-base-url (optional) | >=2.0 | Injects `--base-url` into `base_url` fixture | Can skip if overriding `base_url` fixture directly |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| custom threading fixture | pytest-flask live_server | pytest-flask live_server causes playwright teardown hang (#187); threading.Thread(daemon=True) avoids this entirely |
| custom threading fixture | waitress serve() | waitress is production WSGI; `app.run(use_reloader=False, threaded=True)` is fine for tests only |

**Installation:**
```bash
uv add --dev pytest-playwright
playwright install chromium
```

Add to `pyproject.toml` `[project.optional-dependencies] dev`:
```
"pytest-playwright>=0.5.0",
```

## Architecture Patterns

### Recommended Project Structure
```
tests/
├── conftest.py          # existing — add live_server + brain_dir fixtures here
└── test_gui.py          # new — all 10 Playwright test scenarios
```

### Pattern 1: Session-Scoped Live Server Fixture

**What:** Start Flask in a daemon thread at session scope; all GUI tests share one server instance.
**When to use:** Any test that needs `page.goto()` against the real Flask API.

```python
# In tests/conftest.py (add alongside existing fixtures)
import socket
import threading
import pytest
from engine.api import app as flask_app

@pytest.fixture(scope="session")
def live_server_url(tmp_path_factory, monkeypatch_session=None):
    """Start Flask in a daemon thread; return base URL."""
    # Pick a free port
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    def run():
        flask_app.run(host="127.0.0.1", port=port, use_reloader=False, threaded=True)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    # Give server a moment to bind
    import time; time.sleep(0.5)
    return f"http://127.0.0.1:{port}"
```

**Important:** `monkeypatch` is function-scoped in pytest; for session-scoped server, set `BRAIN_PATH` as an OS env var via `os.environ` before importing `flask_app`, or use a session-scoped `tmp_path_factory` brain dir. See Pattern 2.

### Pattern 2: Session-Scoped Brain Directory + BRAIN_PATH

**What:** Create a shared tmp brain dir for all GUI tests; seed it before server starts.

```python
import os
import pytest
from pathlib import Path

@pytest.fixture(scope="session", autouse=True)
def gui_brain(tmp_path_factory):
    """Create a temp brain dir and set BRAIN_PATH before Flask starts."""
    brain = tmp_path_factory.mktemp("brain")
    # Create subdirs Flask/engine expect
    for d in ["ideas", "meetings", "projects", "people", "work", "files"]:
        (brain / d).mkdir()
    os.environ["BRAIN_PATH"] = str(brain)
    return brain
```

Notes:
- `BRAIN_PATH` must be set **before** `live_server_url` fixture starts Flask, so `gui_brain` must be listed first or marked `autouse=True`.
- `get_connection()` in `engine/db.py` reads `BRAIN_PATH` at call time, so per-test note seeding via direct `conn.execute(INSERT)` works correctly.

### Pattern 3: Playwright `base_url` Override

**What:** Point Playwright's `page.goto("/ui")` at the live server by overriding the `base_url` fixture.

```python
@pytest.fixture(scope="session")
def base_url(live_server_url):
    return live_server_url
```

Playwright's `page` fixture reads `base_url` automatically, so `page.goto("/ui")` resolves correctly.

### Pattern 4: Seeding Notes Per-Test

**What:** Each test inserts a note into SQLite directly (same pattern as `tmp_note` in `test_api.py`) and writes the `.md` file to the `gui_brain` dir.

```python
from engine.db import get_connection
from pathlib import Path

def seed_note(brain: Path, title: str, body: str, tags=None):
    """Write .md file + insert into SQLite. Returns absolute path."""
    import datetime, json
    note_file = brain / "ideas" / f"{title.lower().replace(' ', '-')}.md"
    now = datetime.datetime.utcnow().isoformat()
    note_file.write_text(
        f"---\ntitle: {title}\ntags: {json.dumps(tags or [])}\ntype: idea\n---\n\n{body}\n",
        encoding="utf-8",
    )
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, tags, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (str(note_file), title, "idea", body, json.dumps(tags or []), now, now),
    )
    conn.commit()
    conn.close()
    return str(note_file)
```

### Pattern 5: SSE Live Refresh Test

**What:** Trigger a note creation via API and wait for the sidebar to update without user action. Playwright natively supports `EventSource` (it runs in a real Chromium), so the SSE connection established by `connectSSE()` in app.js works automatically once the page is loaded.

```python
def test_sse_live_refresh(page, live_server_url, gui_brain):
    page.goto("/ui")
    page.wait_for_selector("#note-list")  # initial load

    # Trigger create via API — SSE will broadcast to the open page
    import requests
    requests.post(
        f"{live_server_url}/notes",
        json={"title": "SSE Test Note", "type": "idea", "body": "sse", "brain_path": str(gui_brain)},
    )

    # Sidebar must show new note within 3 seconds
    page.wait_for_selector(
        "#note-list li[data-path]",
        has_text="SSE Test Note",
        timeout=3000,
    )
```

**Caveat:** SSE in threaded Flask dev server requires `threaded=True` (already the right call arg). The app.js hardcodes `API = 'http://127.0.0.1:37491'` — see "Critical Pitfall" below.

### Anti-Patterns to Avoid

- **Using pytest-flask `live_server` fixture with playwright-pytest:** Causes documented teardown hang on session end. Use threading.Thread(daemon=True) instead.
- **Session-scoped server + function-scoped monkeypatch for BRAIN_PATH:** monkeypatch is torn down after each test, unsetting the env var. Use `os.environ` directly in a session-scoped fixture.
- **Not waiting for `#sidebar-loading` to hide before asserting sidebar contents:** The sidebar renders asynchronously after `loadNotes()` resolves. Use `page.wait_for_selector("#sidebar-loading", state="hidden")`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Wait for DOM element | Custom polling loop | `page.locator(...).wait_for()` or `page.wait_for_selector(...)` | Playwright has built-in auto-wait with configurable timeout + state |
| Assert element text | `page.evaluate("document.querySelector(...).textContent")` | `expect(page.locator("...")).to_have_text(...)` | Playwright assertions auto-retry until timeout; no flaky timing issues |
| Check element visibility | Manual JS check | `expect(page.locator("...")).to_be_visible()` | Same auto-retry semantics |
| HTTP request in test | `page.evaluate("fetch(...)")` | `requests.post(...)` (stdlib) | Cleaner; avoids cross-origin issues with hardcoded API port |

## Critical Pitfalls

### Pitfall 1: Hardcoded API Port in app.js

**What goes wrong:** `app.js` line 2 hardcodes `const API = 'http://127.0.0.1:37491'`. The test live server runs on a random port. All `fetch()` calls from the page (loadNotes, openNote, connectSSE, etc.) will hit port 37491, not the test server.

**Why it happens:** The JS was written for the production pywebview flow where the server always runs on 37491.

**How to avoid:** Two options:
1. **Run the test server on port 37491** — simplest; use a fixed test port, ensure no production server is running during tests. Risk: port conflict if `sb-gui` is running.
2. **Make `API` configurable** — inject `window.API_BASE` from the served HTML and use `const API = window.API_BASE || 'http://127.0.0.1:37491'`. This is the correct long-term fix but requires an app.js change.

**Recommendation:** Option 2 (make configurable) — add one line to `api.py`'s `/ui` route to inject `window.API_BASE` into the served HTML, then update `app.js` to use it. This is a small, contained change that makes the app properly testable without port collision risk.

**Warning signs:** Tests see `#sidebar-loading` never disappear; console errors in browser about network requests failing.

### Pitfall 2: BRAIN_PATH Isolation with Session-Scoped Server

**What goes wrong:** The production `engine/api.py` reads `BRAIN_PATH` from `os.environ` at request time (via `_resolve_note_path`, `_get_prefs_path`, etc.). If `BRAIN_PATH` is set to a tmp dir only for the session, all tests share the same brain and can produce ordering-dependent failures.

**How to avoid:** Use `gui_brain` as a session-scoped fixture that sets `BRAIN_PATH` before Flask starts and never unsets it. Individual tests that need isolation should create subdirectories or use unique note titles.

### Pitfall 3: EasyMDE Rendering Delay

**What goes wrong:** After clicking "Edit", the EasyMDE editor is initialized asynchronously. The `#editor-area` textarea becomes visible but the CodeMirror editor wrapping it takes another tick. Interacting with the textarea directly bypasses EasyMDE.

**How to avoid:** Wait for the `.CodeMirror` element to be visible before typing into the editor. For title-sync tests, use the `PUT /notes/<path>` API directly rather than driving the full editor flow — it's more reliable and tests the API path that matters.

### Pitfall 4: SSE Not Working in Threaded Dev Server

**What goes wrong:** Flask's development server `app.run()` doesn't properly handle streaming responses unless `threaded=True`. Without it, SSE connections block and the page hangs.

**How to avoid:** Always pass `threaded=True` to `app.run()` in the test fixture.

### Pitfall 5: `stub_engine_embeddings` Autouse Fixture

**What goes wrong:** The existing `conftest.py` `stub_engine_embeddings` autouse fixture stubs `engine.embeddings` for all tests. This is fine for GUI tests too — we don't need real embeddings. But the session-scoped server imports `engine.api` at collection time, so the module-level `app` object is created before any test runs. Make sure `BRAIN_PATH` is set before the server thread starts.

**How to avoid:** List `gui_brain` as a dependency of `live_server_url` to guarantee ordering.

## Code Examples

### Test: Markdown Rendering
```python
# Source: playwright.dev/python/docs/api/class-page
def test_markdown_rendering(page, gui_brain, seed_note_fn):
    seed_note_fn(gui_brain, "MD Note", "# Heading\n\n**bold text**\n\n- list item")
    page.goto("/ui")
    page.wait_for_selector("#sidebar-loading", state="hidden")
    page.locator("#note-list li[data-path]").first.click()
    viewer = page.locator("#viewer")
    viewer.wait_for(state="visible")
    # Raw markdown characters must not appear in rendered DOM
    assert "#" not in viewer.inner_text()
    assert "**" not in viewer.inner_text()
    # Structural HTML must be present
    page.locator("#viewer h1").wait_for()
    page.locator("#viewer strong").wait_for()
    page.locator("#viewer li").wait_for()
```

### Test: Delete Flow
```python
def test_delete_flow_cancel(page, gui_brain, seed_note_fn):
    seed_note_fn(gui_brain, "Delete Me", "content")
    page.goto("/ui")
    page.wait_for_selector("#sidebar-loading", state="hidden")
    page.locator("#note-list li[data-path]").first.click()
    page.locator("#delete-btn").click()
    # Modal appears
    page.locator("#delete-note-modal").wait_for(state="visible")
    # Cancel — note stays
    page.locator("#delete-modal-cancel").click()
    page.locator("#delete-note-modal").wait_for(state="hidden")
    # Note still in sidebar
    assert page.locator("#note-list li[data-path]").count() > 0
```

### Test: Path Traversal Guard
```python
def test_path_traversal_returns_403(page, live_server_url):
    # Navigate to the UI so we're on the same origin as API calls
    page.goto("/ui")
    status = page.evaluate("""
        async () => {
            const r = await fetch('/api/notes/../../../etc/passwd');
            return r.status;
        }
    """)
    assert status == 403
```

Note: The path traversal test uses `fetch` from the page context. However, since the API is at `http://127.0.0.1:<port>` and the page is served from the same origin, there are no CORS issues. The route path must match what Flask will actually receive after URL normalization. Based on `_resolve_note_path` in `api.py`, the traversal check is: `(Path("/") / note_path).resolve()` must be under `brain_root`. Testing with `GET /notes/../../../etc/passwd` exercises this guard.

### Test: Tag Filtering
```python
def test_tag_filter(page, gui_brain, seed_note_fn):
    seed_note_fn(gui_brain, "Tagged Note", "content", tags=["python"])
    seed_note_fn(gui_brain, "Untagged Note", "content", tags=[])
    page.goto("/ui")
    page.wait_for_selector("#sidebar-loading", state="hidden")
    # Open the tagged note
    page.locator("#note-list li", has_text="Tagged Note").click()
    # Click the tag chip to activate filter
    page.locator("#tag-chips .tag-chip", has_text="python").click()
    # Filter banner must appear
    page.locator("#filter-banner").wait_for(state="visible")
    # Only tagged note visible
    assert page.locator("#note-list li[data-path]").count() == 1
    # Clear filter
    page.locator("#filter-clear").click()
    page.locator("#filter-banner").wait_for(state="hidden")
```

## Selector Map

Derived from `index.html` and `app.js` — all IDs used in tests:

| Feature | Selector | Notes |
|---------|----------|-------|
| Sidebar note list | `#note-list` | Container `ul` |
| Sidebar note item | `#note-list li[data-path]` | Each note `<li>` |
| Sidebar loading | `#sidebar-loading` | Hidden after notes load |
| Filter banner | `#filter-banner` | `display:none` → `flex` on filter |
| Filter clear button | `#filter-clear` | Inside filter banner |
| Note viewer | `#viewer` | Rendered HTML from marked.parse() |
| Tag chips container | `#tag-chips` | Row of `.tag-chip` spans |
| Tag chip | `.tag-chip` | Single-click = filter; double-click = edit |
| Tag chip input | `.tag-chip-input` | Appears after double-click |
| Tag add button | `.tag-add-btn` | "Add tag" button |
| Edit button | `#edit-btn` | Opens EasyMDE editor |
| Save button | `#save-btn` | `display:none` until edit mode |
| Delete button | `#delete-btn` | Triggers delete modal |
| Delete modal | `#delete-note-modal` | `display:none` → `flex` on click |
| Delete confirm | `#delete-modal-confirm` | Confirms deletion |
| Delete cancel | `#delete-modal-cancel` | Closes modal |
| Delete modal filename | `#delete-modal-filename` | Shows filename |
| SSE status dot | `#sse-status` | `.sse-connected` / `.sse-disconnected` |
| Folder section | `.folder-section` | Collapsible sidebar folder |
| Folder header | `.folder-header` | Click to toggle `.collapsed` class |
| Folder notes | `.folder-notes` | `ul` inside folder section |
| Type section | `.type-section` | Nested type group |
| Type header | `.type-header` | Click to toggle `.collapsed` class |
| Collapse toggle | `.collapse-toggle` | `▶` / `▼` inside headers |
| New note button | `#new-note-btn` | Opens new note modal |
| New note modal | `#new-note-modal` | `display:none` → `flex` |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `page.wait_for_selector()` with state param | `page.locator(...).wait_for()` + `expect(...)` assertions | Playwright 1.14+ | `expect()` auto-retries; preferred over raw wait_for_selector |
| `browser.new_page()` in each test | `page` fixture from pytest-playwright | playwright-pytest 0.1+ | Plugin handles lifecycle automatically |

## Open Questions

1. **Hardcoded API port 37491 in app.js**
   - What we know: `const API = 'http://127.0.0.1:37491'` is hardcoded; test server will use a different port
   - What's unclear: Whether to fix at app.js level (inject `window.API_BASE`) or always bind test server to 37491
   - Recommendation: Fix app.js to read `window.API_BASE` — the planner should include this as Wave 0 task before writing any tests. Running on 37491 risks collision with a live `sb-gui` session.

2. **`engine.db` DB_PATH isolation for GUI tests**
   - What we know: `get_connection()` uses a module-level `DB_PATH`. `TestCreateNote` already uses `monkeypatch.setattr(_db, "DB_PATH", tmp_db)` for isolation.
   - What's unclear: Whether the session-scoped live server (which imports `engine.api` once) will pick up per-test DB_PATH changes
   - Recommendation: Session-scoped fixture that sets `DB_PATH` to a tmp db before Flask starts, same as `TestCreateNote._isolate_db` but at session scope.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-playwright (to be installed) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_gui.py -x -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TEST-01 | Markdown renders as HTML | e2e | `pytest tests/test_gui.py::test_markdown_rendering -x` | ❌ Wave 0 |
| TEST-01 | Scroll works (scrollTop changes) | e2e | `pytest tests/test_gui.py::test_scroll -x` | ❌ Wave 0 |
| TEST-01 | Title sync after save | e2e | `pytest tests/test_gui.py::test_title_sync -x` | ❌ Wave 0 |
| TEST-01 | SSE new note appears within 3s | e2e | `pytest tests/test_gui.py::test_sse_live_refresh -x` | ❌ Wave 0 |
| TEST-01 | Delete: modal appears, confirm removes, cancel keeps | e2e | `pytest tests/test_gui.py::test_delete_flow -x` | ❌ Wave 0 |
| TEST-01 | Tag chip edit → save to DOM and API | e2e | `pytest tests/test_gui.py::test_tag_editing -x` | ❌ Wave 0 |
| TEST-01 | Tag filter → sidebar filters, clear restores | e2e | `pytest tests/test_gui.py::test_tag_filter -x` | ❌ Wave 0 |
| TEST-01 | Sidebar section header toggles collapse | e2e | `pytest tests/test_gui.py::test_collapsible_sidebar -x` | ❌ Wave 0 |
| TEST-01 | Path traversal returns 403 | e2e | `pytest tests/test_gui.py::test_path_traversal -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_gui.py -x -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_gui.py` — covers TEST-01 (all 9 e2e scenarios)
- [ ] `playwright install chromium` — browser binary installation step
- [ ] `pyproject.toml` dev deps: add `pytest-playwright>=0.5.0`
- [ ] `app.js` `window.API_BASE` injection — required before any test can run (resolves port 37491 hardcode)
- [ ] Session-scoped `live_server_url`, `gui_brain` fixtures in `conftest.py`

## Sources

### Primary (HIGH confidence)
- [playwright.dev/python/docs/test-runners](https://playwright.dev/python/docs/test-runners) — fixtures, base_url, browser_context_args
- `engine/api.py` (read directly) — all route paths, BRAIN_PATH usage, _resolve_note_path logic
- `engine/gui/static/app.js` (read directly) — all DOM IDs, event handlers, hardcoded API port
- `engine/gui/static/index.html` (read directly) — complete selector inventory
- `tests/conftest.py` (read directly) — existing fixture patterns (brain_root, tmp_path, monkeypatch)
- `tests/test_api.py` (read directly) — tmp_note, DB isolation, BRAIN_PATH monkeypatch pattern

### Secondary (MEDIUM confidence)
- [playwright-pytest GitHub issue #187](https://github.com/microsoft/playwright-pytest/issues/187) — pytest-flask live_server teardown hang with playwright

### Tertiary (LOW confidence)
- WebSearch: threading.Thread(daemon=True) as alternative to pytest-flask for playwright — corroborated by multiple community sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — official docs, pyproject.toml cross-checked
- Architecture (live server): HIGH — verified against actual source files; port 37491 hardcode confirmed in app.js
- Pitfalls: HIGH — hardcoded port is a discovered fact, not hypothesis; SSE threading requirement confirmed by Flask docs behavior
- Selectors: HIGH — derived directly from index.html and app.js source

**Research date:** 2026-03-16
**Valid until:** 2026-06-16 (stable APIs; pytest-playwright API unlikely to change in 90 days)
