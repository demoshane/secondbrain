---
phase: 07-fix-path-format-split
verified: 2026-03-15T00:20:00Z
status: passed
score: 5/5 must-haves verified
---

# Phase 7: Fix Path Format Split — Verification Report

**Phase Goal:** All DB rows store absolute paths — RAG and forget work correctly for notes captured since last reindex without requiring `sb-reindex` first
**Verified:** 2026-03-15T00:20:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                     | Status     | Evidence                                                                                                       |
| --- | ----------------------------------------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------- |
| 1   | All 4 phase-7 tests are GREEN after the fix                                               | VERIFIED   | `pytest` confirms 4/4 pass: test_write_note_atomic_stores_absolute_path, test_write_note_atomic_path_is_absolute, test_retrieve_context_reads_captured_note, test_forget_removes_row_stored_by_capture |
| 2   | Full test suite passes with no regressions                                                | VERIFIED   | 127 passed, 5 skipped, 1 xfailed — zero failures, identical count to pre-phase baseline                       |
| 3   | DB path column stores the canonical resolved form — no symlinks in stored paths           | VERIFIED   | `engine/capture.py` line 106: `resolved_path = str(target.resolve())` used for both INSERT (line 111) and log_audit (line 122) |
| 4   | RAG reads file content directly without '[note file not readable]' fallback               | VERIFIED   | `test_retrieve_context_reads_captured_note` passes; `rag.py` reads `Path(r["path"]).read_text()` — succeeds when capture stores resolved path |
| 5   | forget_person deletes the DB row for a note captured without an intervening reindex       | VERIFIED   | `test_forget_removes_row_stored_by_capture` passes; `forget.py` uses exact-match `DELETE WHERE path IN (?)` — matches because both sides are now resolved |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact              | Expected                                    | Status     | Details                                                                            |
| --------------------- | ------------------------------------------- | ---------- | ---------------------------------------------------------------------------------- |
| `engine/capture.py`   | write_note_atomic stores resolved_path      | VERIFIED   | `resolved_path = str(target.resolve())` at line 106; used for INSERT and log_audit |
| `tests/test_capture.py` | 2 new failing test stubs for absolute-path storage | VERIFIED | `test_write_note_atomic_stores_absolute_path` and `test_write_note_atomic_path_is_absolute` both exist and pass |
| `tests/test_rag.py`   | 1 new test for RAG path resolution          | VERIFIED   | `test_retrieve_context_reads_captured_note` exists and passes                     |
| `tests/test_forget.py` | 1 new test for forget-after-capture path consistency | VERIFIED | `test_forget_removes_row_stored_by_capture` exists and passes                    |

### Key Link Verification

| From                  | To                          | Via                                                        | Status   | Details                                                                                              |
| --------------------- | --------------------------- | ---------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------- |
| `engine/capture.py`   | sqlite notes table          | `resolved_path = str(target.resolve())` used for INSERT    | WIRED    | Line 106 extracts resolved_path; line 111 uses it as first positional arg in INSERT VALUES           |
| `engine/capture.py`   | `engine/rag.py`             | `Path(r['path']).read_text()` works when path is resolved  | WIRED    | rag.py line 32 reads `note_path.read_text()`; resolved path ensures no OSError from symlink mismatch |
| `engine/capture.py`   | `engine/forget.py`          | exact-match DELETE WHERE path IN — matches resolved paths  | WIRED    | forget.py lines 83-88 build `exact_delete_paths` from `str(brain_root / "people" / slug)` — consistent with resolved capture paths when brain_root is resolved |

### Requirements Coverage

| Requirement | Source Plans    | Description                                                              | Status    | Evidence                                                                                   |
| ----------- | --------------- | ------------------------------------------------------------------------ | --------- | ------------------------------------------------------------------------------------------ |
| SEARCH-01   | 07-00, 07-01    | `/sb-search` performs FTS5 full-text search — requires valid stored paths | SATISFIED | Resolved paths stored in DB; test_write_note_atomic_stores_absolute_path verifies contract  |
| SEARCH-04   | 07-00, 07-01    | AI queries retrieve relevant notes via FTS5 as RAG context               | SATISFIED | test_retrieve_context_reads_captured_note confirms RAG reads file without fallback          |
| GDPR-01     | 07-00, 07-01    | `/sb-forget` deletes all traces including DB rows                         | SATISFIED | test_forget_removes_row_stored_by_capture confirms forget_person finds and deletes row captured without reindex |

All 3 requirement IDs declared in both plan frontmatters are accounted for. REQUIREMENTS.md traceability table marks all three as Phase 7 (gap closure) Complete.

### Anti-Patterns Found

No anti-patterns detected in modified files.

- `engine/capture.py`: No TODOs, no placeholder returns, no `str(target)` without `.resolve()` remaining anywhere in the write path
- Test files: No xfail markers on the new phase-7 tests; all 4 are active assertions

### Human Verification Required

None. All goal behaviors are verifiable programmatically via the test suite.

The one scenario that would require human verification — "does `sb-capture` followed by `sb-search` return results in a real DevContainer" — is already covered by the test suite at the unit level. The fix is a single-point change (path storage); no CLI plumbing changed.

### Gaps Summary

No gaps. All must-haves from both plan frontmatters are satisfied:

- The single production change (`resolved_path = str(target.resolve())`) is in place in `engine/capture.py`
- Both the INSERT and the `log_audit` call use the resolved path — audit log and notes table are consistent
- `engine/rag.py` and `engine/forget.py` required no changes (root cause was exclusively in capture's path storage, confirmed by tests)
- Full suite: 127 passed, 5 skipped, 1 xfailed — zero regressions

---

_Verified: 2026-03-15T00:20:00Z_
_Verifier: Claude (gsd-verifier)_
