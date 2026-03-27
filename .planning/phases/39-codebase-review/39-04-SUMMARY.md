---
phase: 39-codebase-review
plan: "04"
subsystem: test-coverage
tags: [audit, test-coverage, mcp, quality]
dependency_graph:
  requires: []
  provides: [39-findings-coverage.md]
  affects: [39-05-PLAN.md, 39-06-PLAN.md, 39-07-PLAN.md]
tech_stack:
  added: []
  patterns: [coverage-matrix, mcp-tool-audit, gap-analysis]
key_files:
  created:
    - .planning/phases/39-codebase-review/39-findings-coverage.md
  modified: []
decisions:
  - MCP tool coverage matrix built by cross-referencing all 22 tools against test_mcp.py function names — 13/22 covered
  - Integration test gap identified as independent finding (COV-05) despite no single file being responsible
metrics:
  duration: 15
  completed: "2026-03-27"
  tasks_completed: 1
  files_modified: 1
---

# Phase 39 Plan 04: Test Coverage Audit Summary

**One-liner:** Test coverage audit revealing 13/22 MCP tools tested, 5 engine modules with no test files, and zero integration tests for the primary MCP workflow.

## What Was Done

Systematically audited the entire test suite (62 test files, ~11k Python lines) against 39 engine modules and all 22 MCP tools. Produced a structured findings document with module-to-test mapping, MCP tool coverage matrix, thin test analysis, integration test gap analysis, and 14 severity-ranked findings.

## Key Findings

### MCP Tool Coverage (13/22 — 59%)
The 9 tools with zero test coverage:
- **`sb_capture_link`** — Chrome extension's primary save path, completely untested
- **`sb_anonymize`** — GDPR operation with two-step token, zero tests (inconsistent with `sb_forget` which has good token coverage)
- **`sb_digest`** — weekly digest generation, zero tests
- **`sb_connections`** — connection surfacing, zero tests
- **`sb_actions_done`** — action item completion, zero tests

Additionally 4 tools (`sb_search`, `sb_actions`, `sb_files`, `sb_recap`) have only shape-level tests with no behavior depth.

### Module Coverage (34/39 — 87%)
Missing test files:
- `engine/config_loader.py` (34 lines) — critical startup component
- `engine/ratelimit.py` (30 lines)
- `engine/merge_cli.py` (37 lines)
- `engine/attachments.py` (90 lines)
- `engine/templates.py` (41 lines) — may be dead code (cross-referenced with D-02)

### Integration Test Gaps
No end-to-end MCP workflow test exists. Each step (capture, search, read) is unit-tested, but the composition — which represents 95% of actual usage — is untested. The forget→cascade→verify-gone pipeline is also only partially tested at MCP layer.

## Findings Summary

| ID | Severity | Gap |
|----|----------|-----|
| COV-01 | High | sb_anonymize zero coverage (GDPR op) |
| COV-02 | High | sb_capture_link zero coverage (Chrome extension path) |
| COV-03 | High | sb_connections + sb_digest zero coverage |
| COV-04 | High | sb_actions_done zero coverage |
| COV-05 | Medium | No MCP-level capture→search→read integration test |
| COV-06 | Medium | engine/attachments.py no test file |
| COV-07 | Medium | engine/merge_cli.py no test file |
| COV-08 | Medium | engine/config_loader.py no test file |
| COV-09 | Medium | engine/ratelimit.py no test file |
| COV-10 | Medium | MCP audit log entries not tested |
| COV-11 | Low | Chrome extension has zero automated tests |
| COV-12 | Low | engine/templates.py no test file (may be dead) |
| COV-13 | Low | test_consolidate.py lacks action archival behavior tests |
| COV-14 | Low | sb_search lacks pagination and empty-result tests |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `39-findings-coverage.md` exists: FOUND
- `39-04-SUMMARY.md` exists: FOUND
- Commit `c166287` exists: FOUND
