---
phase: 15-intelligence-layer
verified: 2026-03-15T19:00:00Z
status: human_needed
score: 12/12 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 11/12
  gaps_closed:
    - "After sb-capture and sb-search, at most one unsolicited offer fires per day total"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Run sb-recap in a real Claude Code session inside the second-brain repo"
    expected: "Coherent 3-5 sentence summary of recent second-brain activity is printed"
    why_human: "LLM output quality is subjective and cannot be asserted programmatically"
  - test: "Start a fresh Claude Code session; observe whether the CLAUDE.md hook triggers sb-recap offer exactly once"
    expected: "Offer fires once at session start, not again on subsequent commands in the same session"
    why_human: "Requires live Claude Code session lifecycle — cannot simulate in pytest"
---

# Phase 15: Intelligence Layer Verification Report

**Phase Goal:** Implement the intelligence layer — budget-gated nudges, action item extraction, stale note detection, connection suggestions, git context detection, and sb-recap/sb-actions CLI commands.
**Verified:** 2026-03-15T19:00:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (15-04 closed INTL-10 budget gate on check_connections)

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `engine/intelligence.py` exists and is importable with all 10 required exports | VERIFIED | All exports confirmed; 18/18 tests GREEN |
| 2 | `engine/db.py` has `action_items` DDL in SCHEMA_SQL and `migrate_add_action_items_table()` | VERIFIED | DDL at line 64; function at line 97; called in `init_schema()` |
| 3 | Action items are extracted from note body at capture time and stored in `action_items` table | VERIFIED | `extract_action_items()` wired into `capture_note()` (lines 253–257 capture.py) |
| 4 | `sb-actions` lists open items newest-first with ID/text/source/date columns | VERIFIED | `actions_main()` prints formatted table header "ID" |
| 5 | `sb-actions --done <id>` marks item done and confirms to stdout | VERIFIED | UPDATE + print confirm in `actions_main` |
| 6 | Notes older than 90 days surface in `get_stale_notes()`; max 5 returned | VERIFIED | Query with cutoff + limit; 18/18 tests GREEN |
| 7 | Notes with `evergreen: true` frontmatter excluded from stale results | VERIFIED | Frontmatter check; TestEvergreenExempt passes |
| 8 | Snoozed notes excluded until recheck date passes | VERIFIED | `stale_snoozed` dict check; 180-day snooze written; TestStaleSnooze GREEN |
| 9 | `budget_available()` returns False when vault < 20 notes or offer already made today | VERIFIED | Full implementation; TestBudgetGate 3/3 GREEN |
| 10 | `sb-recap` with git context prints a summary of recent activity | VERIFIED | `recap_main()` fully implemented; TestRecap GREEN |
| 11 | `sb-recap` without git context and no args prints "No context detected — try sb-recap <name>" | VERIFIED | Line 292 prints hint; TestRecapNoContext GREEN |
| 12 | After sb-capture and sb-search, at most one unsolicited offer fires per day total | VERIFIED | `check_connections()` now gates on `budget_available(conn)` (line 265) and calls `consume_budget()` (line 276); TestConnectionSuggestionBudgetExhausted GREEN |

**Score:** 12/12 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `engine/intelligence.py` | Full implementation of all 10 subsystems | VERIFIED | All exports; budget gate in both check_connections and check_stale_nudge; 18 tests GREEN |
| `engine/db.py` | `action_items` DDL in SCHEMA_SQL + `migrate_add_action_items_table()` | VERIFIED | DDL and migration function confirmed |
| `tests/test_intelligence.py` | 14 test classes covering INTL-01 through INTL-10 including budget exhaustion | VERIFIED | 18 tests, 14 classes, 18 passed |
| `engine/capture.py` | Intelligence hooks after `add_backlinks`, before `return target` | VERIFIED | Lines 253–259: both `check_connections` and `extract_action_items` wired |
| `engine/search.py` | `check_stale_nudge` hook before `conn.close()` | VERIFIED | Lines 102–107: hook in try/except before conn.close() |
| `pyproject.toml` | `sb-recap` and `sb-actions` entry points | VERIFIED | Lines 33–34 confirmed |
| `/Users/tuomasleppanen/.claude/CLAUDE.md` | Session hook line referencing sb-recap | VERIFIED | "Second Brain — Session Context" section present |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/test_intelligence.py` | `engine/intelligence.py` | `from engine.intelligence import` | VERIFIED | Import present; 18 tests pass |
| `engine/db.py init_schema()` | `action_items` table | `SCHEMA_SQL` constant + `migrate_add_action_items_table` | VERIFIED | Both DDL and migration function confirmed |
| `extract_action_items()` | `action_items` table | `conn.execute INSERT INTO action_items` | VERIFIED | Lines 106–109 in intelligence.py |
| `budget_available()` | `intelligence_state.json` | `_load_state()` → `last_offer_date` | VERIFIED | Lines 59–66 in intelligence.py |
| `get_stale_notes()` | `notes` table | `SELECT WHERE updated_at < cutoff` | VERIFIED | Lines 157–161 in intelligence.py |
| `capture_note()` | `check_connections()` + `extract_action_items()` | try/except best-effort after `add_backlinks` | VERIFIED | Lines 253–259 in capture.py |
| `search.main()` | `check_stale_nudge()` | try/except before `conn.close()` | VERIFIED | Lines 102–107 in search.py |
| `check_connections()` | `budget_available(conn)` | guard at top of try block, before `find_similar()` | VERIFIED | Line 265 in intelligence.py — gap now closed |
| `check_connections()` | `consume_budget()` | call after print loop, inside try block | VERIFIED | Line 276 in intelligence.py — gap now closed |
| `recap_main()` | `notes` table | `SELECT WHERE tags/people/title LIKE context_name` | VERIFIED | Lines 298–308 in intelligence.py |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| INTL-01 | 15-01, 15-03 | Once-per-session recap offer in Claude Code | VERIFIED | CLAUDE.md hook added; TestClaudeMdHook GREEN |
| INTL-02 | 15-01, 15-03 | `sb-recap` summarises recent activity for detected context | VERIFIED | `recap_main()` fully implemented; `detect_git_context()` uses /usr/bin/git |
| INTL-03 | 15-01, 15-02 | Action items extracted from meeting notes at capture time | VERIFIED | `extract_action_items()` wired in capture_note(); TestExtractActionItems GREEN |
| INTL-04 | 15-01, 15-02 | User can list open action items via `sb-actions` | VERIFIED | `actions_main()` SELECT + formatted table; TestActionsList GREEN |
| INTL-05 | 15-01, 15-02 | User can mark items complete via `sb-actions --done <id>` | VERIFIED | UPDATE + confirm print; TestActionsDone GREEN |
| INTL-06 | 15-01, 15-02 | Nudge about notes not updated in 90 days (max 5) | VERIFIED | `get_stale_notes()` + `check_stale_nudge()`; TestStaleNudge GREEN |
| INTL-07 | 15-01, 15-02 | `evergreen: true` notes exempt from stale nudges | VERIFIED | Frontmatter check in `get_stale_notes()`; TestEvergreenExempt GREEN |
| INTL-08 | 15-01, 15-02 | Stale nudge re-checks at 180 days | VERIFIED | 180-day snooze written to `stale_snoozed` state; TestStaleSnooze GREEN |
| INTL-09 | 15-01, 15-03 | Connection suggestion after capturing similar note | VERIFIED | `find_similar()` KNN via sqlite-vec; `check_connections()` wired; TestConnectionSuggestion GREEN |
| INTL-10 | 15-01, 15-02, 15-03, 15-04 | Single notification budget — one unsolicited offer per session | VERIFIED | Both `check_connections` and `check_stale_nudge` gate on `budget_available()` and call `consume_budget()`; TestConnectionSuggestionBudgetExhausted GREEN |

---

### Anti-Patterns Found

None. All previously identified blockers resolved.

---

### Human Verification Required

#### 1. sb-recap LLM output quality

**Test:** Run `sb-recap` in the `second-brain` git repo directory
**Expected:** Coherent 3-5 sentence summary of recent second-brain activity; relevant to actual recent notes
**Why human:** LLM output quality and relevance are subjective and cannot be asserted programmatically

#### 2. Once-per-session hook behaviour

**Test:** Start a fresh Claude Code session in any project directory; observe whether the CLAUDE.md hook triggers the sb-recap offer exactly once
**Expected:** Offer fires once at session start, does not repeat on subsequent commands in the same session
**Why human:** Requires live Claude Code session lifecycle — cannot be simulated in pytest

---

### Re-verification Summary

**Gap closed:** `check_connections()` in `engine/intelligence.py` now has a `budget_available(conn)` guard as the first statement inside its `try` block (line 265) and calls `consume_budget()` after the print loop (line 276). This was implemented in Plan 15-04 (commit `336eaa4`).

**New test added:** `TestConnectionSuggestionBudgetExhausted` in `tests/test_intelligence.py` asserts that `check_connections()` produces no output when `budget_available()` returns False. All 18 intelligence tests pass.

**No regressions:** Full suite shows 188 passed, 5 skipped, 1 xfailed. The single pre-existing xfail (`test_blocks_api_key`) is unrelated to Phase 15 and was documented as pre-existing in 15-03.

All automated checks pass. Phase 15 goal is fully achieved. Two items remain for human verification (LLM output quality and session lifecycle behaviour).

---

_Verified: 2026-03-15T19:00:00Z_
_Verifier: Claude (gsd-verifier)_
