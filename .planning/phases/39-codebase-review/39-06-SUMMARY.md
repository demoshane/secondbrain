---
phase: 39
plan: "06"
subsystem: planning
tags: [audit, findings, consolidation, triage]
dependency_graph:
  requires: [39-01, 39-02, 39-03, 39-04, 39-05]
  provides: [39-FINDINGS.md]
  affects: []
tech_stack:
  added: []
  patterns: [severity-calibration, deduplication, remediation-grouping]
key_files:
  created:
    - .planning/phases/39-codebase-review/39-FINDINGS.md
  modified: []
decisions:
  - "31 total findings: 0 Critical, 6 High, 11 Medium, 14 Low — no critical issues found"
  - "api.py:24-25 duplicate import appeared in 3 dimension files — merged into single F-08 (Medium)"
  - "templates.py dead module appeared in architecture + dead-code + coverage — merged into F-02 (High, architecture wins)"
  - "PERF-12 (recap_main closed connection) elevated from Low to High — broken behavior rule applies"
  - "PERF-05, PERF-06, PERF-03, PERF-07 deferred to Phase 40 — medium complexity, not blocking Wave 3"
  - "Remediation grouped into 6 plans (A-F): API hardening, DB indexes+FK, perf queries, dead code, MCP tests, new test files"
metrics:
  duration_seconds: 180
  completed_date: "2026-03-27"
  tasks_completed: 1
  tasks_total: 1
  files_changed: 1
---

# Phase 39 Plan 06: Findings Consolidation Summary

**One-liner:** All 57 raw dimension findings deduplicated and severity-ranked into 31 consolidated findings with remediation grouping across 6 Wave 3 plans.

## What Was Built

`39-FINDINGS.md` — single source of truth for all Phase 39 remediation. Consolidates findings from:
- `39-findings-security.md` — 9 findings (SEC-01 through SEC-09)
- `39-findings-architecture.md` — 13 findings (ARCH-01 through ARCH-15, with duplicates already self-noted)
- `39-findings-performance.md` — 12 findings (PERF-01 through PERF-12)
- `39-findings-coverage.md` — 14 findings (COV-01 through COV-14)
- `39-findings-deadcode.md` — 9 findings (DEAD-01 through DEAD-09)

## Deduplication Applied

| Finding | Appeared In | Merged Into |
|---------|-------------|-------------|
| api.py:24-25 duplicate import | SEC-02, ARCH-01, DEAD-02 | F-08 (Medium) |
| templates.py dead module | ARCH-09, DEAD-01, COV-12 | F-02 (High — arch severity wins) |
| FK CASCADE gap | ARCH-05, ARCH-15 | F-10 (Medium — already self-noted in arch doc) |

## Severity Calibration Notes

- **PERF-12 elevated:** recap_main closed-connection bug was filed under "Low" in the performance audit but is a correctness bug (broken behavior) → elevated to High per D-05.
- **SEC-02 downgraded:** duplicate import finding — Low in arch, Medium in security → security severity wins (D-05 rule: use higher). Filed as F-08 Medium.
- **templates.py:** DEAD-01 = Medium, ARCH-09 = High → High wins. Filed as F-02 High.

## Remediation Grouping

| Group | Plans | Findings | Key Work |
|-------|-------|----------|----------|
| A — API Input Hardening | 1 plan | F-01, F-07, F-08, F-09 | `_int_param` helper, subfolder validation, CSP |
| B — DB Indexes + FK CASCADE | 1 plan | F-10 + index additions | db.py schema migration |
| C — Performance Query Fixes | 1 plan | F-03, F-04, F-05, F-16 | SQL query replacements in intelligence.py + api.py |
| D — Dead Code Removal | 1 plan | F-02, F-11 | Delete templates.py, verify late imports |
| E — MCP Test Coverage | 1 plan | F-06, F-12, F-13, F-14, F-17 | ~10 new test functions in test_mcp.py |
| F — New Test Files | 1 plan | COV-06 through COV-10 | 4 new test files + 1 MCP audit test |

## Accepted Risks Documented

- CORS wildcard (`chrome-extension://*`) — localhost-only binding mitigates
- Host header injection in `/ui` — localhost-only, pywebview controls host header
- `<all_urls>` extension permission — on-demand only, expected browser extension behavior

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — this plan produces a planning document only, no code stubs.

## Self-Check: PASSED
