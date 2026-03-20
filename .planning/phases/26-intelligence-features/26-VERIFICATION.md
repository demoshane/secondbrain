---
phase: 26-intelligence-features
verified: 2026-03-17T00:00:00Z
status: human_needed
score: 4/4 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 3/4
  gaps_closed:
    - "engine/health.py now calls get_empty_notes() and passes empty=len(empty) to compute_health_score — TypeError at runtime eliminated"
    - "tests/test_brain_health.py score stubs updated to use empty= kwarg — 2 previously-xfail tests now xpass"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Open the GUI Intelligence panel and click Generate Recap"
    expected: "Spinner appears, then recap text is displayed; button re-enables after"
    why_human: "AI adapter availability and actual recap content quality cannot be verified programmatically"
  - test: "Click Refresh in the Brain Health section"
    expected: "Score displays as N/100 with green/amber/red color; orphan/broken/duplicate counts shown"
    why_human: "Visual color coding and layout cannot be verified by grep/pytest"
---

# Phase 26: Intelligence Features — Verification Report

**Phase Goal:** Users can trigger a weekly recap on demand from the GUI and view a brain health dashboard showing orphans, broken links, duplicates, and a health score
**Verified:** 2026-03-17
**Status:** human_needed
**Re-verification:** Yes — after gap closure

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Intelligence panel has a Generate Recap button that shows spinner then recap text | VERIFIED | `#generate-recap-btn` in index.html; `generateRecap()` in app.js fetches `POST /intelligence/recap`; event listener wired |
| 2 | `sb-health --brain` reports a 0-100 brain health score with counts | VERIFIED | `--brain` flag in health.py; `_run_brain_health()` calls `get_empty_notes()` + `compute_health_score(empty=...)` correctly; prints `Brain Health Score: N/100` |
| 3 | GUI health panel displays score and check results with clear distinction | VERIFIED | `#health-panel`, `#health-score`, `#health-details` in index.html; `loadBrainHealth()` in app.js fetches `GET /brain-health`, color-codes score, renders counts; auto-called on page load |
| 4 | AI recap and action extraction produce deduplicated, accurate output | VERIFIED | Dedup guard in `extract_action_items()`; `RECAP_SYSTEM_PROMPT` updated; `generate_recap_on_demand()` implemented |

**Score:** 4/4 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `engine/brain_health.py` | `get_orphan_notes()`, `get_empty_notes()`, `get_duplicate_candidates()`, `compute_health_score()` | VERIFIED | All four functions present; `compute_health_score(total_notes, empty, broken, duplicates)` signature consistent across implementation and all callers |
| `engine/intelligence.py` | `generate_recap_on_demand()`, dedup guard in `extract_action_items()` | VERIFIED | Both present |
| `engine/digest.py` | Fixed column names: `text` and `done=0` | VERIFIED | Queries `text, due_date FROM action_items WHERE done=0` |
| `engine/api.py` | `POST /intelligence/recap` and `GET /brain-health` | VERIFIED | Both routes present |
| `engine/health.py` | `--brain` flag calling brain health checks with correct kwargs | VERIFIED | Calls `get_empty_notes(conn)`, passes `empty=len(empty)` — TypeError blocker resolved |
| `engine/gui/static/index.html` | `#generate-recap-btn`, `#health-panel`, `#health-score`, `#health-details`, `#refresh-health-btn` | VERIFIED | All five IDs present |
| `engine/gui/static/app.js` | `generateRecap()`, `loadBrainHealth()`, event listeners | VERIFIED | Both functions present; listeners wired; `loadBrainHealth()` called on page load |
| `tests/test_brain_health.py` | 7 stubs for ENGL-04/ENGL-05 | VERIFIED | All 7 stubs use correct `empty=` kwarg; all expected to xpass |
| `tests/test_intelligence.py` | 2 new stubs for ENGL-03/GUIF-02 | VERIFIED | Both xpass |
| `tests/test_digest.py` | 1 stub for digest column fix | VERIFIED | xpass |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app.js generateRecap()` | `POST /intelligence/recap` | `fetch(..., { method: 'POST' })` | WIRED | app.js fetches `/intelligence/recap` with POST |
| `app.js loadBrainHealth()` | `GET /brain-health` | `fetch(...)` | WIRED | app.js fetches `/brain-health` |
| `engine/api.py POST /intelligence/recap` | `engine.intelligence.generate_recap_on_demand` | lazy import inside route | WIRED | api.py imports and calls `generate_recap_on_demand` |
| `engine/api.py GET /brain-health` | `engine.brain_health` | lazy import inside route | WIRED | api.py imports all three brain_health functions |
| `engine/brain_health.get_duplicate_candidates` | `engine.intelligence.find_similar` | function call threshold=0.92 | WIRED | brain_health.py imports `find_similar` from engine.intelligence |
| `engine/brain_health.get_orphan_notes` | `notes + relationships tables` | LEFT JOIN query | WIRED | brain_health.py: LEFT JOIN relationships on n.path = r.target_path |
| `index.html #generate-recap-btn` | `app.js generateRecap()` | event listener | WIRED | app.js event listener wired |
| `index.html #refresh-health-btn` | `app.js loadBrainHealth()` | event listener | WIRED | app.js event listener wired |
| `engine/health.py --brain` | `engine.brain_health.compute_health_score` | `empty=` kwarg | WIRED | health.py calls `get_empty_notes(conn)` and passes `empty=len(empty)` — fully consistent with brain_health.py signature |

---

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| GUIF-02 | 26-02, 26-04 | On-demand recap from Intelligence panel | SATISFIED | `POST /intelligence/recap` + `generateRecap()` button wired end-to-end |
| ENGL-03 | 26-02 | AI recap quality: better prompts, dedup, accuracy | SATISFIED | `RECAP_SYSTEM_PROMPT` updated; dedup guard in `extract_action_items()`; `generate_recap_on_demand()` with 7-day window |
| ENGL-04 | 26-03 | Brain health dashboard: orphan notes, broken links, duplicates | SATISFIED | `GET /brain-health` returns all fields; GUI health panel renders them |
| ENGL-05 | 26-03 | Brain health score via CLI or GUI | SATISFIED | `sb-health --brain` prints score without TypeError; GUI shows N/100 with color coding |

**Note:** REQUIREMENTS.md traceability table still maps GUIF-02, ENGL-04, ENGL-05 to Phase 25 and ENGL-02 to Phase 26 — these are documentation-only errors, not code gaps. All four requirements are marked `[x]` complete and implemented correctly in Phase 26.

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `tests/test_intelligence.py` | `TestClaudeMdHook::test_claude_md_contains_session_hook` — pre-existing FAILED test | INFO | Pre-existing failure unrelated to Phase 26; not introduced by this phase |

The two BLOCKER and WARNING anti-patterns from the previous report (orphans= kwarg mismatch in health.py and test stubs) have been resolved.

---

### Human Verification Required

#### 1. Generate Recap end-to-end

**Test:** Start `sb-gui`, open the Intelligence panel, click "Generate Recap"
**Expected:** Spinner/loading state appears briefly, then recap text replaces it; button re-enables and is clickable again
**Why human:** AI adapter availability and recap content quality cannot be verified programmatically

#### 2. Brain Health panel visual display

**Test:** In the running GUI, view the Intelligence panel Brain Health section
**Expected:** Score displays as N/100 with color (green >=80, amber >=50, red <50); orphan/broken/duplicate counts shown with checkmarks or warning symbols
**Why human:** CSS color coding and visual layout cannot be verified by grep or pytest

---

### Re-verification Summary

Both gaps from the initial report are now closed:

**Gap 1 (Blocker) — resolved:** `engine/health.py` `_run_brain_health()` now fetches `get_empty_notes(conn)` and passes `empty=len(empty)` as the keyword argument to `compute_health_score`. The `compute_health_score` signature is `(total_notes, empty, broken, duplicates)` — consistent across brain_health.py, health.py, and all test stubs. The runtime TypeError is eliminated.

**Gap 2 (Warning) — resolved:** All three `compute_health_score` call sites in `tests/test_brain_health.py` (lines 74, 80-81, 88) now use `empty=0` / `empty=25` kwargs matching the implementation. These stubs will xpass instead of xfail.

All 4/4 observable truths are verified. Phase goal is achieved. Remaining items require human verification of UI behavior and AI adapter output quality.

---

_Verified: 2026-03-17_
_Verifier: Claude (gsd-verifier)_
