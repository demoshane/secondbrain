# Phase 17: API Layer and Setup Automation - Research

**Researched:** 2026-03-15
**Domain:** Python HTTP API (Flask), Google Drive path detection, Ollama auto-install
**Confidence:** MEDIUM-HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SETUP-01 | `sb-init` auto-detects Google Drive path on macOS and Windows | macOS: `~/Library/CloudStorage/GoogleDrive-*/` glob; Windows: `%USERPROFILE%\GFS\My Drive` or fallback glob on known drive letters |
| SETUP-02 | `sb-init` exits with clear error (non-zero + readable message) if Drive not found — no silent fallback | Existing `validate_drive_mount()` skeleton in `init_brain.py`; extend with detection step before validation |
| SETUP-03 | `sb-init` auto-installs Ollama if not present | macOS: `brew install ollama` or DMG download; Windows: `winget install Ollama.Ollama`; detect via `shutil.which("ollama")` + HTTP probe to `localhost:11434` |
| SETUP-04 | `sb-init` warns user if embedding model download will take significant time (~800 MB first install) | Check model presence via `ollama list` subprocess; print timed warning before `ollama pull` |
</phase_requirements>

---

## Summary

Phase 17 has two parallel tracks: (1) a local HTTP sidecar `engine/api.py` the GUI will call exclusively, and (2) hardening `sb-init` to detect Google Drive and auto-install Ollama without manual steps.

The API track is straightforward: Flask + Waitress is the correct stack for a synchronous local sidecar. All existing engine functions already have proper function signatures; the API layer is thin routing only. The health endpoint is a single `GET /health` route returning JSON. No async is needed — the GUI calls are short-lived and synchronous is fine here.

The setup track is the riskier piece. Google Drive path detection is platform-specific and changes with app versions: macOS uses `~/Library/CloudStorage/GoogleDrive-<email>/` (current, via Apple File Provider, confirmed 2025); Windows uses `%USERPROFILE%\GFS\My Drive` as the standard path for Google Drive for Desktop, but the actual mount letter may vary. Ollama auto-install is easy to detect (`shutil.which` + HTTP probe) but the install mechanism differs by platform — Homebrew on macOS, winget on Windows — and both require the user to have those tools present. For cases where they don't, a clear error with the manual download URL is the correct fallback.

**Primary recommendation:** Use Flask + Waitress for `engine/api.py`. For Drive detection, glob `~/Library/CloudStorage/GoogleDrive-*/` on macOS; probe `%USERPROFILE%\GFS\My Drive` on Windows. For Ollama, detect then install via platform-appropriate package manager, fall back to printed URL on failure.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask | >=3.0 | HTTP routing for `engine/api.py` | Already in ecosystem; zero async complexity; one import; `pyproject.toml` add |
| Waitress | >=3.0 | Production WSGI server (cross-platform, pure Python) | No C deps; runs on Windows and macOS without Gunicorn; standard Flask deployment recommendation |
| flask-cors | >=4.0 | CORS headers for local GUI calls | GUI HTML page needs `Access-Control-Allow-Origin`; one-line setup |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| ollama (already in deps) | >=0.6 | Detect/call Ollama for model list check | Already in `pyproject.toml`; use `ollama.list()` to check if model is installed |
| subprocess (stdlib) | stdlib | Trigger `brew install ollama` / `winget install` | No extra dep; safe for process invocation |
| shutil (stdlib) | stdlib | `shutil.which("ollama")` for binary detection | Already used in `install_native.py` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Flask + Waitress | FastAPI + Uvicorn | FastAPI adds Pydantic + async; overkill for local sync sidecar; more deps to pin |
| Flask + Waitress | Flask dev server | Dev server is not safe for production use; Waitress is the official Flask recommendation |
| `brew install ollama` | Download DMG via `urllib` | DMG approach requires user interaction (drag to Applications); Homebrew is automatable |

**Installation:**
```bash
uv add flask waitress flask-cors
```

---

## Architecture Patterns

### Recommended Project Structure
```
engine/
├── api.py           # Flask app, all HTTP routes, started as sidecar
├── init_brain.py    # Extended with drive_detect() and ollama_ensure()
```

### Pattern 1: Thin API Layer (No Direct Engine Import in GUI)

**What:** `engine/api.py` imports engine functions and exposes them as HTTP endpoints. The GUI never imports `engine/` directly — this is a hard constraint from STATE.md decision: "GUI calls `engine/api.py` only — never imports `engine/` modules directly (C1 hard dependency)."

**When to use:** Always. Every engine capability the GUI needs must go through this layer.

**Example:**
```python
# engine/api.py
from flask import Flask, jsonify, request
from flask_cors import CORS
from engine.db import get_connection
from engine.search import search_notes

app = Flask(__name__)
CORS(app, origins=["null", "file://*", "http://127.0.0.1:*"])

@app.get("/health")
def health():
    return jsonify({"status": "ok"})

@app.get("/notes")
def list_notes():
    conn = get_connection()
    # ... query notes table
    conn.close()
    return jsonify({"notes": [...]})

@app.post("/search")
def search():
    q = request.json.get("query", "")
    conn = get_connection()
    results = search_notes(conn, q)
    conn.close()
    return jsonify({"results": results})

def main():
    from waitress import serve
    serve(app, host="127.0.0.1", port=37491)
```

### Pattern 2: Google Drive Path Detection (macOS)

**What:** Glob `~/Library/CloudStorage/` for `GoogleDrive-*` entries. This path is set by Apple File Provider and is current as of 2025. The email suffix is part of the directory name and varies per account.

**When to use:** Always on macOS (Darwin platform check first).

```python
import platform
from pathlib import Path

def detect_drive_macos() -> Path | None:
    """Return first GoogleDrive-* path under ~/Library/CloudStorage, or None."""
    cloud = Path.home() / "Library" / "CloudStorage"
    candidates = sorted(cloud.glob("GoogleDrive-*"))
    if not candidates:
        return None
    # "My Drive" is the standard subfolder inside the account folder
    for candidate in candidates:
        my_drive = candidate / "My Drive"
        if my_drive.is_dir():
            return my_drive
    return None
```

### Pattern 3: Google Drive Path Detection (Windows)

**What:** Google Drive for Desktop mounts at `%USERPROFILE%\GFS\My Drive` by default on Windows (confirmed via Google Workspace docs, 2025). The actual drive letter can vary if the user changed it (default is G:), but the `GFS` path under USERPROFILE is the reliable filesystem path.

**When to use:** Always on Windows (sys.platform == "win32").

```python
def detect_drive_windows() -> Path | None:
    """Return Google Drive My Drive path on Windows, or None."""
    # Primary: standard GFS path
    candidate = Path.home() / "GFS" / "My Drive"
    if candidate.is_dir():
        return candidate
    # Fallback: check common drive letters G through Z
    for letter in "GHIJKLMNOPQRSTUVWXYZ":
        p = Path(f"{letter}:/My Drive")
        if p.is_dir():
            return p
    return None
```

### Pattern 4: Ollama Detection and Install

**What:** Check binary exists AND service responds. If binary missing, attempt platform install. Warn about model download size before pulling.

```python
import shutil
import subprocess
import sys

OLLAMA_MODEL = "nomic-embed-text"  # ~274 MB; or all-minilm ~22 MB
OLLAMA_LARGE_THRESHOLD_MB = 200

def ollama_is_running() -> bool:
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:11434", timeout=2)
        return True
    except Exception:
        return False

def ollama_ensure(verbose: bool = True) -> bool:
    """Return True if Ollama is ready. Install if missing."""
    if not shutil.which("ollama"):
        if sys.platform == "darwin":
            if shutil.which("brew"):
                subprocess.run(["brew", "install", "ollama"], check=True)
            else:
                print("ERROR: Ollama not found. Install from https://ollama.com/download")
                return False
        elif sys.platform == "win32":
            if shutil.which("winget"):
                subprocess.run(["winget", "install", "Ollama.Ollama"], check=True)
            else:
                print("ERROR: Ollama not found. Install from https://ollama.com/download")
                return False
        else:
            subprocess.run(
                ["sh", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
                check=True,
            )
    return True
```

### Anti-Patterns to Avoid

- **Silent fallback to wrong Drive path:** If detection finds no Drive mount, must `sys.exit(1)` with a readable message — never silently use `~/SecondBrain` as a fallback (SETUP-02 hard requirement).
- **Importing engine modules in GUI:** The GUI layer must call the HTTP API only — never `from engine.search import search_notes` in GUI code.
- **Running Flask dev server in production:** `app.run()` is for development only; always use `waitress.serve()` in `api.py main()`.
- **Assuming Google Drive path is static:** The `GoogleDrive-<email>` suffix changes when the account changes; always glob, never hardcode.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CORS headers | Custom middleware | `flask-cors` | Handles preflight OPTIONS, origin matching, credential rules correctly |
| WSGI production server | Threads in Flask dev server | `waitress` | Dev server is single-threaded, not safe for concurrent GUI calls |
| JSON schema validation in API | Manual `request.json` key checks | Flask's `request.get_json(force=True)` + simple guard | Keep it simple for local API; full Pydantic overkill here |
| Model size estimation | Hardcoded bytes | `ollama list` output parsing | Ollama CLI reports model size; avoids stale hardcoded numbers |

---

## Common Pitfalls

### Pitfall 1: Port 37491 Already in Use

**What goes wrong:** If a stale `sb-api` process is still running, starting a new one fails with `Address already in use`.

**Why it happens:** GUI or user starts two instances; or a crash leaves a socket open.

**How to avoid:** In `api.py main()`, check if port is in use before starting; optionally emit a clear error message pointing to `lsof -i :37491`.

**Warning signs:** `OSError: [Errno 48] Address already in use` on startup.

### Pitfall 2: macOS File Provider Path Missing on Fresh Install

**What goes wrong:** `~/Library/CloudStorage/` directory exists but contains no `GoogleDrive-*` subfolder because the user has Drive installed but not signed in.

**Why it happens:** Google Drive app installed but account not configured.

**How to avoid:** Distinguish between "Drive not installed" and "Drive not signed in" in the error message. Check `~/Library/CloudStorage/` existence first; then check for `GoogleDrive-*` entries.

**Warning signs:** Empty `CloudStorage/` directory.

### Pitfall 3: Ollama Installed but Not Running on macOS

**What goes wrong:** `shutil.which("ollama")` returns a path but `localhost:11434` times out — Ollama binary exists but service hasn't been started.

**Why it happens:** Homebrew installs the binary but doesn't start the service.

**How to avoid:** After install (and on any `sb-init` run), check HTTP probe; if binary exists but service not running, run `ollama serve` as a background subprocess or instruct user to start Ollama app.

**Warning signs:** Binary found, HTTP probe fails, timeout.

### Pitfall 4: Windows Drive Letter Variability

**What goes wrong:** Code hardcodes `G:\My Drive` but user configured a different letter.

**Why it happens:** Google Drive for Desktop lets users pick any drive letter.

**How to avoid:** Try `%USERPROFILE%\GFS\My Drive` first (filesystem path, not drive letter dependent), then iterate drive letters as fallback.

### Pitfall 5: CORS Rejecting `file://` Origin

**What goes wrong:** pywebview-based GUI (Phase 18) loads from `file://` origin; browser security blocks API calls.

**Why it happens:** Default CORS policy denies `null` origin (which `file://` becomes).

**How to avoid:** In `CORS(app, origins=[...])`, explicitly allow `"null"` and `"file://*"`. This is safe since the API is bound to `127.0.0.1` only.

---

## Code Examples

### Health Endpoint
```python
# Source: standard Flask pattern
@app.get("/health")
def health():
    return jsonify({"status": "ok", "port": 37491})
```

### Waitress Server Start
```python
# Source: https://flask.palletsprojects.com/en/stable/deploying/waitress/
from waitress import serve
serve(app, host="127.0.0.1", port=37491, threads=4)
```

### Note List Endpoint (example shape)
```python
@app.get("/notes")
def list_notes():
    conn = get_connection()
    rows = conn.execute(
        "SELECT path, type, title, created_at FROM notes ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return jsonify({"notes": [dict(r) for r in rows]})
```

### Drive Detection Entry Point
```python
def detect_drive_path() -> Path | None:
    """Platform-dispatch Drive detection."""
    import sys
    if sys.platform == "darwin":
        return detect_drive_macos()
    elif sys.platform == "win32":
        return detect_drive_windows()
    return None  # Linux not supported

def assert_drive_or_exit() -> Path:
    path = detect_drive_path()
    if path is None:
        print(
            "[sb-init] ERROR: Google Drive not found.\n"
            "  macOS: ensure Google Drive for Desktop is installed and signed in.\n"
            "  Windows: ensure Google Drive for Desktop is installed (https://drive.google.com/drive/download).",
            file=sys.stderr,
        )
        sys.exit(1)
    return path
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `/Volumes/Google Drive` (macOS) | `~/Library/CloudStorage/GoogleDrive-*/` | ~2021 (Apple File Provider) | Must use glob — old path no longer exists |
| Gunicorn for Flask | Waitress (cross-platform) | Ongoing | Windows support; no C extension |
| `flask.run()` for local servers | `waitress.serve()` | Flask 2.x+ | Thread safety; proper shutdown |

**Deprecated/outdated:**
- `/Volumes/Google Drive`: Old Google Drive app mount point; replaced by Apple File Provider path.
- `app.run(debug=True)` in production: Dev server only; Waitress is the replacement.

---

## Open Questions

1. **Ollama model name for embeddings**
   - What we know: `init_brain.py` currently writes `ollama/llama3.2` as the pii_model in `config.toml`; Phase 14 decision says Ollama is default embedding provider with `all-MiniLM-L6-v2`
   - What's unclear: Which Ollama model is actually used for embeddings (nomic-embed-text? all-minilm?)  — the Phase 14 embedding stack deferred fastembed; current embeddings.py should be checked
   - Recommendation: Read `engine/embeddings.py` at plan time to confirm the model name before writing the SETUP-04 size warning copy

2. **sb-api as a separate script entry point**
   - What we know: `pyproject.toml` currently has no `sb-api` entry point
   - What's unclear: Should `engine/api.py` be invoked via `sb-api` CLI entry point (natural pattern) or started by the GUI inline?
   - Recommendation: Add `sb-api = "engine.api:main"` to `[project.scripts]` so it can be started from launchd or the GUI subprocess

3. **Ollama service start after Homebrew install on macOS**
   - What we know: `brew install ollama` installs binary but does not start service
   - What's unclear: Does `sb-init` need to also start the service (via `ollama serve &` or launchctl)? Or just check and prompt?
   - Recommendation: At planning time, decide: start service inline (risky — leaves background process) or print instructions. Recommend printing a clear instruction for now.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=7.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_api.py tests/test_init_brain.py -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SETUP-01 | `detect_drive_macos()` returns path when `GoogleDrive-*` dir exists | unit | `uv run pytest tests/test_init_brain.py::TestDriveDetection -x` | ❌ Wave 0 |
| SETUP-01 | `detect_drive_windows()` returns path when GFS dir exists | unit | `uv run pytest tests/test_init_brain.py::TestDriveDetectionWindows -x` | ❌ Wave 0 |
| SETUP-02 | `assert_drive_or_exit()` calls `sys.exit(1)` when no Drive found | unit | `uv run pytest tests/test_init_brain.py::TestDriveExitOnMissing -x` | ❌ Wave 0 |
| SETUP-03 | `ollama_ensure()` returns False and prints error when binary missing and no brew/winget | unit | `uv run pytest tests/test_init_brain.py::TestOllamaEnsure -x` | ❌ Wave 0 |
| SETUP-04 | `sb-init` prints size warning before model pull | unit | `uv run pytest tests/test_init_brain.py::TestOllamaModelSizeWarning -x` | ❌ Wave 0 |
| API | `GET /health` returns 200 `{"status": "ok"}` | unit | `uv run pytest tests/test_api.py::TestHealthEndpoint -x` | ❌ Wave 0 |
| API | `GET /notes` returns JSON list | unit | `uv run pytest tests/test_api.py::TestNotesList -x` | ❌ Wave 0 |
| API | `POST /search` with query returns results | unit | `uv run pytest tests/test_api.py::TestSearch -x` | ❌ Wave 0 |
| API | `GET /notes/<path>` returns note content | unit | `uv run pytest tests/test_api.py::TestReadNote -x` | ❌ Wave 0 |
| API | `GET /actions` returns action items | unit | `uv run pytest tests/test_api.py::TestActionItems -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_api.py tests/test_init_brain.py -q`
- **Per wave merge:** `uv run pytest -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_api.py` — covers all API endpoint requirements
- [ ] `tests/test_init_brain.py` — new classes `TestDriveDetection`, `TestDriveExitOnMissing`, `TestOllamaEnsure`, `TestOllamaModelSizeWarning` appended to existing file
- [ ] `engine/api.py` — new file; Flask app skeleton
- [ ] Framework install: `uv add flask waitress flask-cors` — none of these are in `pyproject.toml` yet

---

## Sources

### Primary (HIGH confidence)
- Official Flask deployment docs — Waitress deployment pattern, `waitress.serve()` signature
- `engine/init_brain.py` (project codebase) — existing `validate_drive_mount()`, `main()` structure
- `engine/paths.py` (project codebase) — `BRAIN_ROOT = Path.home() / "SecondBrain"` baseline
- `scripts/install_native.py` (project codebase) — `find_uv()`, `shutil.which()` pattern
- `.planning/STATE.md` — "GUI calls `engine/api.py` only" hard constraint

### Secondary (MEDIUM confidence)
- WebSearch verified: macOS `~/Library/CloudStorage/GoogleDrive-*/` path — confirmed current as of 2025 via Apple File Provider architecture
- WebSearch verified: Windows `%USERPROFILE%\GFS\My Drive` — confirmed via Google Workspace admin docs 2025
- WebSearch: Waitress pure-Python WSGI server, cross-platform, Windows supported — confirmed via Flask official docs
- WebSearch: Ollama detection via `localhost:11434` HTTP probe — confirmed via Ollama docs

### Tertiary (LOW confidence)
- Windows drive letter fallback (G-Z scan): inferred from user-configurable nature of Google Drive mount letter — needs validation on a real Windows machine
- Ollama Homebrew start behavior: needs confirmation that `brew install ollama` does not auto-start service

---

## Metadata

**Confidence breakdown:**
- Standard stack (Flask + Waitress): HIGH — both confirmed via official Flask docs
- API architecture: HIGH — directly from project constraint in STATE.md
- Google Drive macOS path: HIGH — confirmed Apple File Provider pattern, current 2025
- Google Drive Windows path: MEDIUM — primary path confirmed, drive-letter fallback inferred
- Ollama install automation: MEDIUM — individual steps confirmed; combined flow needs integration testing
- Pitfalls: MEDIUM — derived from known platform behaviors and project patterns

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable ecosystem; Google Drive path could change with major app update)
