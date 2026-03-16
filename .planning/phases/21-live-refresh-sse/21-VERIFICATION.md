---
phase: 21-live-refresh-sse
verified: 2026-03-16T14:00:00Z
status: human_needed
score: 8/8 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 6/8
  gaps_closed:
    - "Conflict banner: easyMDE !== null guard now in handleNoteEvent (app.js:284) — editor open is the primary trigger regardless of isDirty"
    - "False deletion on save: suppress_next_delete() added to watcher.py; api.py save_note calls it after os.replace(); _fire skips deleted broadcast for suppressed paths within 500ms"
    - "GUI sidecar thread count: threads=8 in gui/__init__.py line 46 (was threads=4)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Conflict banner on external edit while editor is open"
    expected: "Open note, click Edit (do not type). In terminal: echo '# ext' >> note.md. Within 2s a banner 'Note was updated externally' appears with Keep/Load buttons. Editor content is unchanged."
    why_human: "easyMDE lifecycle and SSE delivery timing cannot be deterministically reproduced in unit tests"
  - test: "No false 'Note was deleted' message on save"
    expected: "Open note, click Edit, type something, click Save. Viewer shows updated content. No 'Note was deleted' message appears."
    why_human: "Depends on macOS FSEvents coalescing during os.replace() — non-deterministic in unit tests"
  - test: "Conflict banner Keep/Load buttons work"
    expected: "Keep button dismisses banner, editor stays open with content intact. Load button closes editor, reloads viewer with external content."
    why_human: "Interactive DOM event handling requires manual testing"
  - test: "Status dot turns green within acceptable delay"
    expected: "Dot visible in topbar; turns green within ~5s of launch. 5s delay is accepted as cosmetic."
    why_human: "Visual element; timing depends on EventSource handshake with live server"
---

# Phase 21: Live Refresh SSE Verification Report (Re-verification)

**Phase Goal:** Notes created or edited anywhere (GUI, CLI, file watcher daemon) appear in the sidebar and viewer without restarting the application
**Verified:** 2026-03-16
**Status:** human_needed — all automated checks pass; human verification required for two previously-failed items now fixed
**Re-verification:** Yes — after gap closure (plans 21-05 and 21-06)

---

## Re-verification Summary

Previous score: 6/8 (gaps_found). Two items failed human verification in plan 21-04:

1. **Conflict banner (CRITICAL):** isDirty guard was present but never reached — editor silently discarded unsaved content.
2. **False deletion on save (BUG):** watchdog emitted a `deleted` event for the target path during `os.replace()` atomic rename on macOS.

Both are now fixed in code. Automated evidence is conclusive. Human re-verification is required to confirm interactive behavior.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GET /events returns 200 with Content-Type text/event-stream | VERIFIED | api.py:85-106 — route exists, mimetype set; regression: SSE registry still intact (lines 57-81) |
| 2 | NoteChangeHandler ignores non-.md files and files/ subdirectory changes | VERIFIED | watcher.py:116-123 — `_is_note()` unchanged; regression: still present |
| 3 | NoteChangeHandler debounces rapid modifications (300ms per-path timer) | VERIFIED | watcher.py:125-134 — per-path timer logic unchanged; regression: still present |
| 4 | NoteChangeHandler emits created/modified/deleted with relative path | VERIFIED | watcher.py:136-148 — `_fire` logic unchanged except suppression guard added at line 139-142 |
| 5 | _broadcast() delivers named SSE frames to all subscriber queues; drops on full | VERIFIED | api.py:74-81 — unchanged; regression: still present |
| 6 | Observer starts when sb-api starts and when sb-gui starts | VERIFIED | api.py:315 calls start_note_observer(); gui/__init__.py:54-55 calls start_note_observer() after health check |
| 7 | If the open note is modified externally and editor has unsaved changes, conflict banner appears instead of silent reload | VERIFIED (code) | app.js:284 — `if (easyMDE !== null)` is the primary guard; showConflictBanner() called unconditionally when editor is open; human re-verify required |
| 8 | False "note deleted" notification does NOT appear on normal save | VERIFIED (code) | watcher.py:84-97 — `_save_suppress` set + `suppress_next_delete()`; api.py:24 imports it; api.py:192 calls it after `os.replace()`; `_fire` guards at lines 139-142; human re-verify required |

**Score:** 8/8 truths verified (automated evidence complete; items 7 and 8 require human confirmation of interactive behavior)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_api_sse.py` | SSE endpoint + subscriber registry test coverage | VERIFIED | Unchanged from initial verification — 3 tests |
| `tests/test_note_watcher.py` | NoteChangeHandler unit test coverage | VERIFIED | Unchanged — 5 tests; suppression set is module-level and compatible |
| `engine/api.py` | SSE subscriber registry, /events route, start_note_observer(), suppress_next_delete import | VERIFIED | Lines 24, 57-119, 192, 315 all present and wired |
| `engine/watcher.py` | NoteChangeHandler class + suppress_next_delete() | VERIFIED | Lines 84-97: `_save_suppress`, `suppress_next_delete`, `_clear_suppress`; lines 139-142: guard in `_fire` |
| `engine/gui/__init__.py` | Observer startup + threads=8 | VERIFIED | Line 46: `"threads": 8`; line 54-55: `start_note_observer()` called after health check |
| `engine/gui/static/app.js` | handleNoteEvent with easyMDE !== null guard | VERIFIED | Line 284: `if (easyMDE !== null)` primary guard; line 289: `else if (isDirty)` defensive fallback; line 293: `else openNote()` |
| `engine/gui/static/index.html` | status dot element | VERIFIED | Regression check: `sse-status` element previously confirmed present |
| `engine/gui/static/style.css` | status dot styles | VERIFIED | Regression check: `.sse-dot`, `.sse-connected`, `.sse-disconnected` previously confirmed present |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `engine/api.py start_note_observer()` | `engine/watcher.NoteChangeHandler` | instantiates handler, passes _broadcast | WIRED | api.py:112-114 — unchanged |
| `engine/gui/__init__.py _start_sidecar()` | `engine/api.start_note_observer()` | called after health check passes | WIRED | gui/__init__.py:54-55 — unchanged |
| `engine/api.py event_stream()` | `_subscribe() / _unsubscribe()` | generator with finally block | WIRED | api.py:87 subscribes, api.py:100 unsubscribes in finally — unchanged |
| `app.js connectSSE()` | `http://127.0.0.1:37491/events` | new EventSource(`${API}/events`) | WIRED | app.js:301 — unchanged |
| `app.js handleNoteEvent()` | `loadNotes()` | called on every note event | WIRED | app.js:268 — unchanged |
| `app.js easyMDE change event` | `isDirty = true` | easyMDE.codemirror.on('change', ...) | WIRED | app.js:102 — unchanged |
| `app.js handleNoteEvent easyMDE !== null` | `showConflictBanner()` | primary guard in modified/created branch | WIRED | app.js:284-288 — NEW: replaced `isDirty` guard with `easyMDE !== null` |
| `engine/api.py save_note` | `engine/watcher._save_suppress` | suppress_next_delete(str(p)) after os.replace() | WIRED | api.py:24 imports suppress_next_delete; api.py:192 calls it — NEW |
| `engine/watcher.NoteChangeHandler._fire` | `_save_suppress` set | skips deleted broadcast if path in set | WIRED | watcher.py:139-142 — NEW: guard before broadcast |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| GUIX-01 | 21-01, 21-02, 21-03, 21-05, 21-06 | New notes and edits reflected in GUI without restarting (live refresh) | SATISFIED (pending human re-verify) | SSE infrastructure wired end-to-end; conflict banner guard fixed (easyMDE !== null); false-deletion suppression added; REQUIREMENTS.md line 11 already marks [x] Complete — consistent with plan 21-06 SUMMARY requirements-completed: [GUIX-01] |

**REQUIREMENTS.md discrepancy resolved:** GUIX-01 is now correctly marked `[x] Complete` at line 11 and `Complete` in the progress table at line 62. This was flagged as incorrect in the initial verification (phase 21-04 left it open); plans 21-05 and 21-06 completed it and updated REQUIREMENTS.md accordingly.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `engine/gui/static/app.js` | 297-307 | `_sseWasConnected` starts false; first `onopen` sets it true and calls `loadNotes()` — double load on initial connect (also called at init line 325) | Info | Cosmetic double fetch on startup; no functional issue |

No blockers found. The `threads=4` warning from the initial verification is resolved (now `threads=8` at line 46).

---

## Human Verification Required

### 1. Conflict Banner on External Edit While Editor Is Open

**Test:** Open any note in the GUI. Click Edit (do NOT type anything). In a terminal: `echo "# external change" >> ~/SecondBrain/SOME_NOTE.md`. Within 2 seconds, observe the GUI.
**Expected:** A yellow banner "Note was updated externally" appears with "Keep my edits" and "Load new version" buttons. Editor content is unchanged.
**Why human:** easyMDE instantiation and SSE delivery timing are interactive — the fix relies on `easyMDE !== null` being true when the SSE event fires, which cannot be deterministically reproduced in unit tests.

### 2. No False "Note Deleted" Message on Save

**Test:** Open a note, click Edit, type something, click Save (or Cmd+S).
**Expected:** Note saves; viewer shows updated content. No "Note was deleted" message appears anywhere in the GUI.
**Why human:** Depends on macOS FSEvents coalescing behavior during `os.replace()` — the 500ms suppression window must outlast the actual FSEvents propagation delay, which is non-deterministic in unit tests.

### 3. Conflict Banner Keep/Load Buttons Work

**Test:** Trigger the conflict banner (repeat test 1). Click "Keep my edits". Then trigger again and click "Load new version".
**Expected:** Keep: banner dismisses, editor stays open with content intact. Load: banner dismisses, editor closes, viewer reloads with external content.
**Why human:** Interactive DOM event handling requires manual verification of state transitions.

### 4. Status Dot Timing (cosmetic)

**Test:** Launch `sb-gui`. Observe the topbar dot.
**Expected:** Dot visible; turns green within ~5s of launch. 5s delay is accepted as cosmetic.
**Why human:** Visual element; timing depends on EventSource handshake with live server.

---

## Gaps Summary

No automated gaps remain. Both previously-blocked items are now fixed in code:

**Gap 1 (Conflict banner) — CLOSED:** `handleNoteEvent` at app.js:284 now uses `easyMDE !== null` as primary guard. Any open editor session is protected from silent auto-reload regardless of whether the user has typed yet. The `isDirty` check is retained as a defensive fallback.

**Gap 2 (False deletion on save) — CLOSED:** `suppress_next_delete(str(p))` is called in `save_note` (api.py:192) immediately after `os.replace()`. `NoteChangeHandler._fire` skips the `deleted` broadcast when the path is in `_save_suppress` (watcher.py:139-142). The 500ms auto-clear via `threading.Timer` bounds the suppression window.

**Threads fix — CLOSED:** `gui/__init__.py` line 46 now uses `threads=8`, matching `api.py main()`. No thread pool exhaustion risk under SSE load.

All three items confirmed present in code. Human re-verification of interactive behavior is the final gate before GUIX-01 can be considered fully closed.

---

_Verified: 2026-03-16_
_Verifier: Claude (gsd-verifier)_
_Re-verification: Yes — after gap closure plans 21-05 and 21-06_
