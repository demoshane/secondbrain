---
phase: 17-api-layer-and-setup-automation
verified: 2026-03-15T20:30:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 17: API Layer and Setup Automation Verification Report

**Phase Goal:** A stable local HTTP API exists for the GUI to call, and `sb-init` completes a working setup without any manual Drive or Ollama configuration steps.
**Verified:** 2026-03-15T20:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `sb-init --detect-drive` auto-detects Google Drive on macOS/Windows; exits non-zero with readable error if not found | VERIFIED | `detect_drive_macos()` globs `CloudStorage/GoogleDrive-*/My Drive`; `detect_drive_windows()` checks GFS + G-Z letters; `assert_drive_or_exit()` calls `sys.exit(1)` with "Google Drive not found" message to stderr |
| 2 | `sb-init` auto-installs Ollama when binary missing; warns before ~800 MB model download | VERIFIED | `ollama_ensure()` invokes `brew install ollama` / `winget install Ollama.Ollama`; falls back to URL when no package manager; `ollama_model_size_warning()` prints "~800 MB" before `ollama pull` |
| 3 | `engine/api.py` exposes all engine functions via HTTP on `127.0.0.1:37491`; GUI can retrieve notes, search, read a note, and get actions without importing any `engine/` module | VERIFIED | All 5 endpoints implemented and wired: `/health`, `/notes` (DB query), `/search` (delegates to `search_notes()`), `/notes/<path>` (file read + 404), `/actions` (delegates to `list_actions()`); Waitress on `127.0.0.1:37491` |
| 4 | `GET /health` responds so the GUI can detect sidecar readiness | VERIFIED | `@app.get("/health")` returns `{"status": "ok", "port": 37491}` with HTTP 200 |

**Score:** 4/4 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `engine/api.py` | Flask app with /health, /notes, /search, /notes/\<path\>, /actions + Waitress main() | VERIFIED | 72 lines; all 5 endpoints present; `main()` uses `waitress.serve(app, host="127.0.0.1", port=37491, threads=4)`; no `app.run()` call |
| `engine/init_brain.py` | 6 new functions + main() wired + `--detect-drive` flag | VERIFIED | `detect_drive_macos()`, `detect_drive_windows()`, `detect_drive_path()`, `assert_drive_or_exit()`, `ollama_ensure()`, `ollama_model_size_warning()` all present; main() calls `ollama_ensure()` + `ollama_model_size_warning()` after schema init; `--detect-drive` argparse flag present |
| `tests/test_api.py` | 9 test stubs covering all API behaviors | VERIFIED | 9 tests across 5 classes (TestHealthEndpoint x2, TestNotesList x2, TestSearch x2, TestReadNote x1, TestActionItems x2) |
| `tests/test_init_brain.py` | Extended with TestDriveDetection, TestDriveExitOnMissing, TestOllamaEnsure, TestOllamaModelSizeWarning | VERIFIED | All 4 new classes present; imports `detect_drive_macos`, `ollama_ensure` from `engine.init_brain` |
| `pyproject.toml` | flask>=3.0, waitress>=3.0, flask-cors>=4.0, sb-api entry point | VERIFIED | All 3 deps present in `[project.dependencies]`; `sb-api = "engine.api:main"` in `[project.scripts]` |
| `engine/intelligence.py` | `list_actions(conn, done)` helper | VERIFIED | `def list_actions(conn, done: bool = False) -> list[dict]` at line 121; queries `action_items` table and returns list of dicts |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `engine/api.py` | `engine.db.get_connection` | per-request connection | WIRED | `from engine.db import get_connection` at top; called in every endpoint handler |
| `engine/api.py` | `engine.search.search_notes` | POST /search | WIRED | `from engine.search import search_notes`; called as `search_notes(conn, query)` in `/search` handler |
| `engine/api.py` | `engine.intelligence.list_actions` | GET /actions | WIRED | `from engine.intelligence import list_actions`; called as `list_actions(conn, done=False)` in `/actions` handler |
| `engine/init_brain.py main()` | `assert_drive_or_exit()` | `--detect-drive` flag path | WIRED | `if args.detect_drive: detected = assert_drive_or_exit()` — called before Drive mount validation |
| `engine/init_brain.py main()` | `ollama_ensure()` + `ollama_model_size_warning()` | after schema init | WIRED | `if ollama_ensure(): ollama_model_size_warning()` called at line 288-292 |
| `tests/test_api.py` | `engine.api` | `from engine.api import app` | WIRED | Module-level import confirmed; Flask test client fixture wires `app.test_client()` |
| `tests/test_init_brain.py` | `engine.init_brain` new symbols | `detect_drive_macos`, `ollama_ensure` imports | WIRED | Module-level import of new symbols confirmed at lines 13, 16 |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SETUP-01 | 17-00, 17-01, 17-02 | `sb-init` auto-detects Google Drive on macOS and Windows | SATISFIED | `detect_drive_macos()` + `detect_drive_windows()` + `detect_drive_path()` platform dispatch in `engine/init_brain.py`; wired via `--detect-drive` flag |
| SETUP-02 | 17-00, 17-01, 17-02 | `sb-init` exits with clear error if Drive not found — no silent fallback | SATISFIED | `assert_drive_or_exit()` calls `sys.exit(1)` with "Google Drive not found" to stderr; no fallback to wrong path |
| SETUP-03 | 17-00, 17-01, 17-02 | `sb-init` auto-installs Ollama if not present | SATISFIED | `ollama_ensure()` tries `brew install ollama` on macOS, `winget install Ollama.Ollama` on Windows; returns False with download URL when no package manager |
| SETUP-04 | 17-00, 17-01, 17-02 | `sb-init` warns user if model download will take significant time (~800 MB) | SATISFIED | `ollama_model_size_warning()` prints `"~800 MB"` before `ollama pull` when model absent; uses ollama SDK `ollama.list()` with subprocess fallback |

All 4 requirements satisfied. No orphaned requirements found (REQUIREMENTS.md marks all 4 as Complete / Phase 17).

---

### Anti-Patterns Found

No blockers or warnings detected.

| File | Pattern | Severity | Notes |
|------|---------|----------|-------|
| `engine/api.py` | None | — | No TODOs, no stubs, no `return null`, no `app.run()` |
| `engine/init_brain.py` | `except Exception: pass` in `ollama_model_size_warning()` | Info | Intentional — Ollama unavailability is non-fatal; embeddings.py handles at runtime |

---

### Human Verification Required

#### 1. Drive detection on a real macOS machine with Google Drive installed

**Test:** Run `sb-init --detect-drive` on a machine with Google Drive for Desktop signed in.
**Expected:** Prints detected path (e.g. `/Users/you/Library/CloudStorage/GoogleDrive-you@example.com/My Drive`) and proceeds.
**Why human:** `detect_drive_macos()` relies on filesystem glob — cannot verify real Drive mount in test environment.

#### 2. Ollama auto-install on a machine without Ollama

**Test:** Uninstall Ollama, then run `sb-init`. Confirm brew/winget install is triggered and model size warning appears before download.
**Expected:** "Installing Ollama via Homebrew..." then "Downloading nomic-embed-text (~800 MB)..." printed before pull begins.
**Why human:** Requires a live machine state change; subprocess calls to brew/winget cannot be safely run in CI.

#### 3. Flask sidecar reachable from a GUI-equivalent caller

**Test:** Run `sb-api` in background, then `curl -s http://127.0.0.1:37491/health`.
**Expected:** `{"port": 37491, "status": "ok"}` returned with 200.
**Why human:** Waitress daemon startup + network binding cannot be tested in unit tests.

---

### Gaps Summary

No gaps. All 4 success criteria verified against the actual codebase.

- `engine/api.py` is substantive (72 lines, 5 real endpoints, all wired to engine modules, no stubs).
- `engine/init_brain.py` extended with 6 real functions (not stubs), all wired into `main()`.
- CORS configured for `null`, `file://*`, `http://127.0.0.1:*` — pywebview compatible.
- Boundary condition: `assert_drive_or_exit` uses `base_path` kwarg (not `home`) to match the RED test scaffold — tests win over plan spec, which is the declared convention.
- `list_actions()` was added to `engine/intelligence.py` during plan 17-01 as a deviation (it was referenced in the plan's interface spec but did not exist); function is real, tested, and wired.

---

_Verified: 2026-03-15T20:30:00Z_
_Verifier: Claude (gsd-verifier)_
