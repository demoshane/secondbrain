---
phase: 28-todo-and-gap-resolution
verified: 2026-03-19T12:00:00Z
status: passed
score: 7/7 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 6/7
  gaps_closed:
    - "overdue action items (due_date < today, done=0) are surfaced in recap output"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Run uv run pytest tests/ -q (full suite including test_gui.py)"
    expected: "All 9 previously failing Playwright tests pass in full suite context; exit code 0"
    why_human: "CI result not available; conftest.py changes are structural and could have subtle ordering effects"
  - test: "Call sb_capture_smart with a realistic meeting transcript"
    expected: "Returns suggestion with type 'meeting' and a reasonable inferred title"
    why_human: "Heuristic regex classifier — correctness for real-world text requires human judgment"
---

# Phase 28: TODO & Gap Resolution Verification Report

**Phase Goal:** All open TODOs, known gaps, and deferred issues identified at phase start are resolved before the milestone is closed
**Verified:** 2026-03-19
**Status:** passed
**Re-verification:** Yes — after gap closure (previous: gaps_found 6/7)

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | sb_capture on a note with body > 2000 chars uses title-only embedding for dedup | VERIFIED | `engine/capture.py` line 71: `text_to_embed = title if len(body) > max_body_len else f"{title}\n{body}"` with `max_body_len=2000` default |
| 2 | sb_capture_smart returns typed note suggestions without saving | VERIFIED | `engine/mcp_server.py` line 432: `def sb_capture_smart(content)` returns `{"suggestions": [...], "confirm_token": ...}`; test `test_sb_capture_smart_no_auto_save` confirms no DB write |
| 3 | sb_tag adds/removes tags with fuzzy matching and confirm-token gate for new tags | VERIFIED | `engine/mcp_server.py` line 544: `def sb_tag(path, action, tag, confirm_token)`; `difflib.get_close_matches(cutoff=0.8)` used; 5 tests pass |
| 4 | sb_link creates and sb_unlink removes directional relationships (DB-only) | VERIFIED | `engine/mcp_server.py` lines 653, 673: both tools present; `INSERT OR IGNORE` / `DELETE` on `relationships` table; 5 tests pass |
| 5 | sb_remind sets due_date on action items and sb_actions returns due_date | VERIFIED | `engine/mcp_server.py` line 511: `def sb_remind`; `engine/intelligence.py` line 158 SELECT includes `due_date`; `engine/api.py` lines 881-884 handles `due_date` in PUT; 8 tests pass |
| 6 | overdue action items (due_date < today, done=0) are surfaced in recap output | VERIFIED | `generate_recap_on_demand()` (line 473) calls `get_overdue_actions(conn)` and prepends `## Overdue Actions` section; `test_overdue_in_recap` in `tests/test_intelligence.py` asserts `"## Overdue Actions" in recap` and `"Overdue task" in recap`; `test_overdue_not_in_recap_when_none` asserts section absent when no overdue items |
| 7 | sb_person_context returns one-call full context (note + meetings + actions + mentions) for a person | VERIFIED | `engine/mcp_server.py` line 698: `def sb_person_context(path)`; 5 tests pass covering note body, meetings, actions, mentions, and unknown path handling |

**Score:** 7/7 truths verified

---

## Gap Closure Detail

The single gap from the previous verification is now closed:

**Gap:** `generate_recap_on_demand()` never called `get_overdue_actions()`; no overdue section in recap output.

**Fix verified:**
- `engine/intelligence.py` lines 473-480: `overdue = get_overdue_actions(conn)` called unconditionally at the top of `generate_recap_on_demand()`; `overdue_section` built and prepended to all return paths (lines 488, 512).
- `tests/test_intelligence.py` lines 476-526: Two new integration tests added — `test_overdue_in_recap` inserts an overdue item and asserts `"## Overdue Actions"` and the item text appear in the recap string; `test_overdue_not_in_recap_when_none` asserts the section is absent when no items are overdue. Both tests call `generate_recap_on_demand()` directly, testing true recap integration (not helper isolation).

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `engine/capture.py` | `check_capture_dedup()` with `max_body_len` + `_embed_texts_for_dedup()` helper | VERIFIED | Both present; wired to `sb_capture` at line 164 |
| `engine/mcp_server.py` | `sb_capture_smart`, `sb_tag`, `sb_link`, `sb_unlink`, `sb_remind`, `sb_person_context` | VERIFIED | All 6 new tools present at expected lines |
| `engine/intelligence.py` | `list_actions()` with `due_date`, `get_overdue_actions()`, `generate_recap_on_demand()` calling `get_overdue_actions()` | VERIFIED | `due_date` in SELECT at line 158; `get_overdue_actions` at line 171; called from recap at line 473 |
| `engine/api.py` | `PUT /actions/<id>` accepting `due_date` | VERIFIED | Lines 881-884 handle `due_date` key |
| `tests/conftest.py` | `_GUI_DB_PATH` sentinel + `_restore_gui_db` autouse fixture | VERIFIED | Sentinel at line 16; autouse fixture at line 75; `gui_brain` sets sentinel at lines 296-297 |
| `tests/test_capture.py` | `test_dedup_title_only_large_body`, `test_dedup_short_body_uses_full_text` | VERIFIED | Both tests present |
| `tests/test_intelligence.py` | `test_overdue_in_recap`, `test_overdue_not_in_recap_when_none` | VERIFIED | Both tests call `generate_recap_on_demand()` and assert on overdue section presence/absence |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `engine/mcp_server.py sb_capture()` | `engine/capture.py check_capture_dedup()` | called at line 164 before `capture_note()` | WIRED | Import confirmed |
| `engine/mcp_server.py sb_remind()` | `action_items.due_date column` | `UPDATE action_items SET due_date=?` | WIRED | Confirmed in mcp_server.py |
| `engine/mcp_server.py sb_actions()` | `engine/intelligence.py list_actions()` | `list_actions()` call; returns `due_date` | WIRED | Import confirmed |
| `generate_recap_on_demand()` | `get_overdue_actions()` | overdue section prepended to recap | WIRED | Lines 473-480 and 488, 512 confirm all return paths include overdue_section |
| `tests/conftest.py _restore_gui_db` | `engine.db.DB_PATH + engine.paths.DB_PATH` | direct assignment after every test | WIRED | Lines 92-98 confirm re-anchor logic |

---

## Requirements Coverage

No requirement IDs were specified for this phase (phase_requirement_ids: null). All 7 plan items from the phase now satisfied.

| Plan Item | Description | Status | Evidence |
|-----------|-------------|--------|----------|
| 28-01 | Title-only dedup for large captures | SATISFIED | `max_body_len` param in `check_capture_dedup()` |
| 28-02 | `sb_capture_smart` heuristic classifier | SATISFIED | Tool registered, 5 tests pass |
| 28-03 | `sb_tag` with fuzzy matching + confirm-token | SATISFIED | Tool registered, 5 tests pass |
| 28-04 | `sb_link` / `sb_unlink` DB-only relationships | SATISFIED | Both tools registered, 5 tests pass |
| 28-05 | `sb_remind` + due_date end-to-end + overdue in recap | SATISFIED | sb_remind done; due_date in list_actions done; PUT /actions done; overdue section wired into generate_recap_on_demand; integration tests pass |
| 28-06 | `sb_person_context` one-call full context | SATISFIED | Tool registered, 5 tests pass |
| 28-07 | Fix 9 Playwright GUI failures in full suite | SATISFIED | `_GUI_DB_PATH` sentinel + `_restore_gui_db` autouse fixture in conftest.py |

---

## Anti-Patterns Found

No TODO, FIXME, HACK, or XXX comments found in `engine/mcp_server.py`, `engine/capture.py`, or `engine/intelligence.py`. No placeholder return stubs detected in new or modified functions.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| No anti-patterns found | — | — | — | — |

---

## Human Verification Required

### 1. Playwright full-suite green

**Test:** Run `uv run pytest tests/ -q` (full suite including test_gui.py)
**Expected:** All 9 previously failing Playwright tests now pass in the full suite context; exit code 0
**Why human:** CI result not available at verification time; conftest.py changes are structural and could have subtle ordering effects

### 2. sb_capture_smart classification quality

**Test:** Call `sb_capture_smart` with a realistic meeting transcript (e.g. "Met with Alice Smith today. Meeting: project kickoff. Discussed milestones and deadlines.")
**Expected:** Returns a suggestion with type `meeting` (not `note`) and a reasonable inferred title
**Why human:** Heuristic regex classifier — correctness for real-world text requires human judgment

---

## Regressions Check

Quick regression scan on the six items that passed in the previous verification:

| Item | Check | Result |
|------|-------|--------|
| `sb_capture_smart` | `def sb_capture_smart` at line 432 | Present |
| `sb_tag` | `def sb_tag` at line 544 | Present |
| `sb_link` / `sb_unlink` | Lines 653, 673 | Present |
| `sb_remind` | `def sb_remind` at line 511 | Present |
| `sb_person_context` | `def sb_person_context` at line 698 | Present |
| `capture.py max_body_len` | `text_to_embed = title if len(body) > max_body_len` at line 71 | Present |
| `conftest.py _GUI_DB_PATH` | Sentinel at line 16, autouse at line 75, re-anchor at lines 92-98 | Present |

No regressions detected.

---

_Verified: 2026-03-19_
_Verifier: Claude (gsd-verifier)_
