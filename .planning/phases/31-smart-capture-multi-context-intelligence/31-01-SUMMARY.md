---
phase: 31-smart-capture-multi-context-intelligence
plan: "01"
subsystem: mcp-server, engine
tags: [smart-capture, segmentation, pii-classification, mcp-tools]
dependency_graph:
  requires: []
  provides: [engine/segmenter.py, engine/smart_classifier.py, sb_capture_smart]
  affects: [engine/mcp_server.py, tests/test_smart_capture.py, tests/test_mcp.py]
tech_stack:
  added: []
  patterns: [two-pass-segmentation, entity-based-pii-detection, auto-save-no-confirm]
key_files:
  created:
    - engine/segmenter.py
    - engine/smart_classifier.py
    - tests/test_smart_capture.py
  modified:
    - engine/mcp_server.py
    - tests/test_mcp.py
decisions:
  - "sb_capture_smart auto-saves (no confirm_token round-trip) — Phase 31 contract"
  - "xfail stubs must patch both engine.paths.BRAIN_ROOT and mcp_mod.BRAIN_ROOT for isolation"
  - "Phase 28-02 test_mcp.py tests updated to match new auto-save contract (notes key, not suggestions)"
metrics:
  duration_minutes: 25
  completed_date: "2026-03-20"
  tasks_completed: 2
  files_changed: 5
---

# Phase 31 Plan 01: Smart Capture Segmentation Foundation Summary

Two-pass segmentation engine (`segment_blob`) and entity-based PII classifier (`classify_smart`) implemented, with `sb_capture_smart` rewritten to auto-save atomically — no confirm round-trip.

## What Was Built

### Task 1: Segmenter + Smart Classifier + xfail Test Stubs (commit 5626392)

**`engine/segmenter.py`** — `segment_blob(content: str) -> list[dict]`:
- Pass 1 (structural): splits on `#{1,3}`, `---`, date stamps `YYYY-MM-DD`, `RE:`, `Subject:`
- Protected regions: fenced code blocks and markdown tables masked before splitting so their content is never split
- Pass 2 (name-cluster): detects topic shifts in segments >500 chars by checking people entity changes between paragraphs
- Short segment merge: segments <50 chars or <2 lines fold into adjacent segment
- Max 20 cap: merges smallest pairs until count ≤ 20
- Per-segment type classification: link (URL), meeting, person, project, idea, note
- Returns `[{"title", "type", "body", "links", "entities"}, ...]`

**`engine/smart_classifier.py`** — `classify_smart(body, user_sensitivity) -> (level, reason)`:
- Entity-based PII patterns: SSN, Finnish hetu, credit card (Visa/MC), email, phone
- Never-downgrade rule: `max(user_supplied, detected)` by level ordering
- Phone guard: requires ≥7 digits to avoid false positives

**`tests/test_smart_capture.py`**:
- 24 passing unit tests for segmenter and classifier
- 12 xfail(strict=False) stubs for CAP-01 through CAP-11 + performance

### Task 2: sb_capture_smart Rewrite (commit b9c355f)

**`engine/mcp_server.py`** `sb_capture_smart` rewritten:
- Replaced stub (suggestions + confirm_token) with real two-pass implementation
- Calls `segment_blob(content)` → saves each segment via `capture_note()` atomically
- Creates `co-captured` relationships between all saved notes via `itertools.combinations`
- Infers meeting→person cross-links: person note paths added to meeting `links` field
- Returns `{"status": "created", "notes": [...], "capture_session": UUID, "count": N}`
- No `confirm_token` in response

**`tests/test_mcp.py`** Phase 28-02 tests updated:
- 5 tests updated from old contract (`suggestions`, `confirm_token`, `no_auto_save`) to new (`notes`, no `confirm_token`, `auto_saves`)

## Deviations from Plan

### Auto-fix Issues

**1. [Rule 1 - Bug] Missing `engine.paths` import in first xfail stub**
- **Found during:** Task 1 verification
- **Issue:** `test_capture_smart_returns_suggestions` referenced `engine.paths` without importing it
- **Fix:** Added `import engine.paths` before the `monkeypatch.setattr` call
- **Files modified:** tests/test_smart_capture.py
- **Commit:** b9c355f

**2. [Rule 1 - Bug] xfail stubs leaked to real ~/SecondBrain**
- **Found during:** Task 2 verification
- **Issue:** All 12 xfail stubs patched `engine.paths.BRAIN_ROOT` but not `mcp_mod.BRAIN_ROOT`. Since `mcp_server.py` imports `BRAIN_ROOT` at module level via `from engine.paths import BRAIN_ROOT`, patching only `engine.paths` doesn't affect the already-bound name in `mcp_server`
- **Fix:** Added `monkeypatch.setattr(mcp_mod, "BRAIN_ROOT", isolated_brain)` to all 12 stubs
- **Files modified:** tests/test_smart_capture.py
- **Commit:** b9c355f

**3. [Rule 1 - Bug] Phase 28-02 tests in test_mcp.py expected old stub contract**
- **Found during:** Task 2 verification
- **Issue:** 5 tests from Phase 28-02 asserted `suggestions` key, `confirm_token`, and that `sb_capture_smart` does NOT save — all inverted by the Phase 31-01 rewrite
- **Fix:** Updated all 5 tests to match new auto-save contract; renamed `test_sb_capture_smart_no_auto_save` → `test_sb_capture_smart_auto_saves`, `test_sb_capture_smart_returns_confirm_token` → `test_sb_capture_smart_no_confirm_token`
- **Files modified:** tests/test_mcp.py
- **Commit:** b9c355f

## Test Results

```
73 passed, 7 xfailed, 7 xpassed in 40.92s
```

- All segmenter unit tests: PASS
- All `classify_smart` unit tests: PASS
- 12 xfail stubs: collected (7 xfailed, 7 xpassed — stubs whose assertions already hold)
- Existing MCP tests: PASS
- Pre-existing `test_links.py` failures (Phase 30 scope): out of scope, not modified

## Success Criteria Check

1. `segment_blob("# Meeting\n...\n---\n# Person\n...")` returns 2+ segments — PASS
2. `classify_smart("Call me at +358 50 123 4567", "public")` returns `("pii", "detected: phone number")` — PASS
3. `sb_capture_smart` with multi-section input saves N notes and returns `capture_session` UUID — PASS
4. No `confirm_token` in `sb_capture_smart` response — PASS
5. All 12 xfail stubs collected by pytest — PASS

## Self-Check: PASSED

- engine/segmenter.py: FOUND
- engine/smart_classifier.py: FOUND
- tests/test_smart_capture.py: FOUND
- engine/mcp_server.py: FOUND
- Commit 5626392 (Task 1): FOUND
- Commit b9c355f (Task 2): FOUND
