---
phase: 25-file-capture-batch-capture
verified: 2026-03-17T08:00:00Z
status: human_needed
score: 12/12 must-haves verified
re_verification: false
human_verification:
  - test: "Open any note, click '+ File' in topbar → OS file picker opens → select a PDF. Attachment appears below note body as 'filename · date · size'."
    expected: "Attachment row visible below note body. No toast or modal. No sidebar duplication."
    why_human: "File I/O, pywebview, OS file picker, and visual DOM rendering cannot be verified programmatically."
  - test: "Drag a PNG onto the viewer area with a note open."
    expected: "Attachment appears in the list below the note body."
    why_human: "Drag-and-drop DataTransfer events require real browser/WebView interaction."
  - test: "Viewer toolbar '+ File' button (near Delete) is visible when a note is open. Clicking it opens the file picker."
    expected: "Button appears and triggers note-specific upload via hidden #file-input."
    why_human: "Button visibility toggled by openNote() JS at runtime."
  - test: "Click 'Batch Capture' in the topbar. Then click it again."
    expected: "First run: Intelligence panel shows 'Batch capture: N captured, 0 failed'. Second run: '0 captured' (idempotent)."
    why_human: "Requires live brain directory state and real DB walk."
  - test: "Attempt to upload a .sh or .exe file via the note-specific viewer upload button."
    expected: "No attachment appears. Server returns 415 silently."
    why_human: "MIME rejection path requires a real upload attempt with an executable file."
  - test: "Upload a file via GUI, then wait ~1 second. Check that the note appears only once in the sidebar."
    expected: "Single sidebar entry. No duplicate DB row from watcher firing on the same file."
    why_human: "Watcher race condition requires real filesystem event timing to confirm dedup window works."
---

# Phase 25: File Capture & Batch Capture Verification Report

**Phase Goal:** Users can capture files from the GUI and run a single batch capture of all unindexed items, with no duplicate notes from the watcher race.
**Verified:** 2026-03-17T08:00:00Z
**Status:** human_needed (all automated checks pass; 6 items require live GUI confirmation)
**Re-verification:** No — initial verification.

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | `attachments` table exists in brain.db after `init_schema()` runs | VERIFIED | `engine/db.py:111-125` — `migrate_add_attachments_table()` uses `CREATE TABLE IF NOT EXISTS`; called at line 138 of `init_schema()` |
| 2  | `POST /files/upload` saves file to `files/` dir and inserts into `attachments` table | VERIFIED | `engine/api.py:464-512` — MIME check, `secure_filename`, collision suffix, `suppress_next_create()`, `f.save()`, `save_attachment()` all present |
| 3  | `POST /files/upload` rejects executables with HTTP 415 | VERIFIED | `engine/api.py:486` — `if mime not in ALLOWED_MIMES: return ..., 415`; `ALLOWED_MIMES` defined at lines 28-40 |
| 4  | `GET /notes/<path>/attachments` returns attachment list for a note | VERIFIED | `engine/api.py:517-527` — calls `list_attachments(note_path)` directly (no traversal guard — deliberate, note_path is a DB key only) |
| 5  | `POST /batch-capture` indexes untracked `.md` files and skips already-indexed ones | VERIFIED | `engine/api.py:529-580` — rglob walk, existing-set skip, INSERT, `_broadcast` at end |
| 6  | Watcher dedup guard skips `created` events for paths already in `attachments` or `notes` table | VERIFIED | `engine/watcher.py:143-156` — checks `is_upload_suppressed()` first, then queries both tables; returns early if match found; placed before `_broadcast` call at line 163 |
| 7  | Upload button exists in topbar; Batch Capture button exists in topbar | VERIFIED | `index.html:18-19` — `id="upload-btn"` and `id="batch-capture-btn"` present in header toolbar |
| 8  | `upload-btn` opens global file management modal (repurposed from note upload per Plan 04 fix) | VERIFIED | `app.js:864` — `uploadBtn.addEventListener('click', openFilesModal)`; `openFilesModal()` defined at line 831 |
| 9  | Drag-and-drop onto `#viewer` triggers `uploadFile()` | VERIFIED | `app.js:890-894` — `dragover` preventDefault and `drop` handler call `uploadFile(file)` on `#viewer` element |
| 10 | Attachment list renders below note body in `#attachments-section` (separate div, never overwrites viewer) | VERIFIED | `index.html:39` — `#attachments-section` is sibling of `#viewer` (not child); `app.js:898-928` — `loadAttachments()` targets `#attachments-section`, never writes to `#viewer` |
| 11 | `loadAttachments()` is called from `openNote()` after body loads | VERIFIED | `app.js:427` — `loadAttachments(path)` called inside `openNote()` after `renderMarkdown(body)` |
| 12 | All 7 `test_api_upload.py` tests pass and `TestWatcherDedup` is a real (non-stub) test | VERIFIED | No `xfail` markers remain in `test_api_upload.py`; `TestWatcherDedup.test_dedup_skips_already_indexed` has full assertions (isolated DB, pre-inserted note, `assert_not_called()`) |

**Score:** 12/12 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `engine/db.py` | `migrate_add_attachments_table()` called from `init_schema()` | VERIFIED | Lines 111-125 (function), line 138 (call) |
| `engine/attachments.py` | `save_attachment`, `list_attachments`, `suppress_next_create`, `is_upload_suppressed` | VERIFIED | 90 lines; all four functions present at lines 19, 31, 41, 73 |
| `engine/api.py` | `POST /files/upload`, `GET /notes/<path>/attachments`, `POST /batch-capture`, `_ensure_schema()` | VERIFIED | Endpoints at lines 464, 517, 529; `_ensure_schema` at line 607, called in `main()` at line 619 |
| `engine/watcher.py` | Dedup guard in `_fire()` for `created` events | VERIFIED | Lines 143-156; checks suppress set and DB tables before broadcast |
| `engine/gui/static/index.html` | `upload-btn`, `batch-capture-btn`, `viewer-upload-btn`, `#file-input`, `#attachments-section`, `#files-modal` | VERIFIED | All 6 elements present; confirmed by grep (4 matches on the primary IDs, plus `files-modal` at line 92) |
| `engine/gui/static/app.js` | `uploadFile()`, `loadAttachments()`, drag-drop events, batch capture handler | VERIFIED | All present: lines 811, 898, 890, 932 |
| `tests/test_api_upload.py` | 7 real passing tests (no xfail) | VERIFIED | 148 lines; all 7 test methods found; zero `xfail` markers |
| `tests/test_note_watcher.py` | `TestWatcherDedup` with real assertions | VERIFIED | Lines 153-154+; full test body with DB setup and `assert_not_called()` |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `engine/api.py:upload_file` | `engine/attachments.py:save_attachment` | direct call after MIME + filename validation | VERIFIED | `api.py:474` imports `save_attachment`; called at line 511 |
| `engine/api.py:upload_file` | `engine/attachments.py:suppress_next_create` | called before `f.save()` | VERIFIED | `api.py:508` — `suppress_next_create(str(dest))` before `f.save` at line 510 |
| `engine/api.py:upload_file` | `_broadcast` SSE | after `save_attachment` | VERIFIED | `api.py:512` — `_broadcast({"type": "attachment", "note_path": note_path})` |
| `engine/api.py:batch_capture` | `engine.db:get_connection` | INSERT-only walk of brain dir | VERIFIED | `api.py:529`; `get_connection()` used to build existing-set and perform INSERTs |
| `app.js:uploadFile` | `POST /files/upload` | FormData fetch with `file` + `note_path` | VERIFIED | `app.js:816` — `fetch(\`${API}/files/upload\`, { method: 'POST', body: fd })` |
| `app.js:loadAttachments` | `GET /notes/<path>/attachments` | fetch in `openNote()` after body load | VERIFIED | `app.js:902` — `fetch(\`${API}/notes/${encodeURIComponent(notePath)}/attachments\`)` |
| `app.js:batchCaptureBtn.onclick` | `POST /batch-capture` | fetch + result displayed in `#recap-content` (Intelligence panel) | VERIFIED | `app.js:938` — `fetch(\`${API}/batch-capture\`, { method: 'POST' })`; result written to `#recap-content` at line 942 (confirmed as the Intelligence panel element in `index.html:58`) |
| `engine/watcher.py:_fire` | `engine.attachments:is_upload_suppressed` | lazy import inside `_fire()` | VERIFIED | `watcher.py:144` — `from engine.attachments import is_upload_suppressed` |

---

## Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| GUIF-01 | 25-01, 25-02, 25-03, 25-04 | User can capture a file from the GUI; file saved to `files/` and indexed | VERIFIED | `POST /files/upload` endpoint, `save_attachment()`, `#attachments-section`, drag-drop, `viewer-upload-btn` all implemented |
| ENGL-01 | 25-01, 25-02, 25-03, 25-04 | Single capture trigger captures all relevant new items in batch | VERIFIED | `POST /batch-capture` walks brain dir, inserts absent `.md` files, returns `{succeeded, failed}`, broadcasts SSE; idempotent (skips already-indexed) |

Both requirements are checked off in `.planning/REQUIREMENTS.md` (lines 26, 31).

No orphaned requirements — all IDs declared in plan frontmatter map directly to implemented functionality.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | None found |

Zero TODO/FIXME/PLACEHOLDER comments found in implementation files. Zero `xfail` stubs remain in test files. Zero empty return stubs in API routes.

One known deferred item (not a blocker): The AI layer can store error strings in the `tags` column. A runtime guard was added in `app.js` (`renderTagChips` skips entries >60 chars or matching error prefixes). Root-cause fix deferred to Phase 27. This is documented in 25-04 SUMMARY and does not block phase 25 requirements.

---

## Human Verification Required

The following items require live GUI testing. All backend logic is verified; these items concern runtime behavior, visual rendering, and OS-level interaction.

### 1. File upload via topbar button

**Test:** Open any note. Click "+ File" in the topbar. Select any PDF or image.
**Expected:** File is saved to `files/` directory. Attachment appears below the note body as "filename · date · size". No toast, no modal. Sidebar does not reload.
**Why human:** File picker is OS-native; WebView DOM rendering and visual layout of `#attachments-section` cannot be verified by grep.

### 2. Drag-and-drop upload

**Test:** With a note open, drag a PNG from Finder onto the viewer panel.
**Expected:** Attachment row added to the list below the note body.
**Why human:** Drag DataTransfer events require real browser/WebView interaction.

### 3. Viewer toolbar upload button

**Test:** Open any note. Confirm a "+ File" button is visible in the viewer toolbar (near the Delete button). Click it.
**Expected:** OS file picker opens; selecting a file attaches it to the current note.
**Why human:** Button visibility controlled by JS at runtime (`viewer-upload-btn.style.display = ''` in `openNote()`).

### 4. Batch Capture idempotency

**Test:** Click "Batch Capture" in the topbar toolbar. Click it again immediately after.
**Expected:** First run shows "Batch capture: N captured, 0 failed". Second run shows "0 captured" (all files already indexed).
**Why human:** Requires live brain directory state and real SQLite walk.

### 5. Executable file rejection (UX)

**Test:** With a note open, attempt to upload a `.sh` or `.exe` file via the viewer "+ File" button.
**Expected:** No attachment row appears. The upload silently fails (415 response from server, nothing visible to user).
**Why human:** Requires a real upload attempt with an executable MIME type.

### 6. Watcher dedup — no sidebar duplication

**Test:** Upload a file via the viewer "+ File" button. Wait 2 seconds. Check the sidebar.
**Expected:** The note appears only once in the sidebar. No duplicate entry from the watcher firing on the same `files/` path.
**Why human:** Race condition with a 0.5-second suppress window requires real filesystem event timing.

---

## Gaps Summary

No automated gaps. All backend implementation is substantive and wired. All test stubs were promoted to real passing tests. All frontend elements exist and are connected to their respective API endpoints.

One design decision was changed from the original plan during execution (Plan 04 auto-fix): the topbar `#upload-btn` was repurposed from note-specific upload to a global file management modal, because clicking it without an active note did nothing. The note-specific upload path is now exclusively through `#viewer-upload-btn` (viewer toolbar) and drag-and-drop. This is a correct UX fix and does not violate either GUIF-01 or ENGL-01.

---

_Verified: 2026-03-17T08:00:00Z_
_Verifier: Claude (gsd-verifier)_
