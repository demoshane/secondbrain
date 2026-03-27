---
phase: 39-codebase-review
plan: "01"
subsystem: security-audit
tags: [security, audit, api, mcp, chrome-extension]
dependency_graph:
  requires: []
  provides: [39-findings-security.md]
  affects: [39-05-PLAN.md, 39-06-PLAN.md, STATE.md]
tech_stack:
  added: []
  patterns: [security-findings-format]
key_files:
  created:
    - .planning/phases/39-codebase-review/39-findings-security.md
  modified: []
decisions:
  - "SEC-01 (High): 8 unguarded int() calls across api.py — fix in remediation phase"
  - "SEC-04 (Medium): sb_files subfolder allows path traversal — needs validation guard"
  - "No SQL injection found — all queries use parameterized placeholders"
  - "PII routing gap in sb_person_context documented but not escalated to High"
  - "CORS all chrome-extension:// accepted as design decision (localhost-only mitigates)"
metrics:
  duration_seconds: 179
  completed_date: "2026-03-27"
  tasks_completed: 1
  files_created: 1
---

# Phase 39 Plan 01: Security Audit Summary

Security audit of all API surfaces, MCP tools, and Chrome extension. Wave 1 findings produced.

## One-liner

Security audit found 1 High (unguarded int() params → HTTP 500), 4 Medium (path traversal in sb_files, duplicate import, delete_file path design, CSP absent + innerHTML gap), and 4 Low findings; zero SQL injection vulnerabilities; PII routing gap in sb_person_context noted.

## Tasks Completed

| Task | Description | Outcome |
|------|-------------|---------|
| 1 | Security audit — backend API + MCP + extension | Complete — 39-findings-security.md created |

## Findings Summary

| ID | Severity | Description | Fix Required |
|----|----------|-------------|-------------|
| SEC-01 | High | Unguarded int() on 8 query params in api.py → HTTP 500 | Yes |
| SEC-02 | Medium | Duplicate BRAIN_ROOT import api.py:24-25 | Yes (trivial) |
| SEC-03 | Medium | delete_file accepts abs path — guard correct, design risk documented | No (guard works) |
| SEC-04 | Medium | sb_files subfolder not validated → path traversal outside files_dir | Yes |
| SEC-05 | Medium | No explicit CSP in manifest; innerHTML escapeHtml single-quote gap | Yes |
| SEC-06 | Low | CORS accepts any chrome-extension:// — localhost-only mitigates | No |
| SEC-07 | Low | Host header injection in /ui script tag | No (localhost-only) |
| SEC-08 | Low | /ui/prefs PUT no size/schema validation | No (localhost-only) |
| SEC-09 | Low | all_urls permission scope in extension | No (accepted risk) |

**Critical: 0 | High: 1 | Medium: 4 | Low: 4**

## Key Decisions Made

1. SEC-01 is High not Critical — it causes HTTP 500 availability issues but does not expose data. Fix is straightforward (try/except wrapper or helper function).
2. SEC-04 (sb_files path traversal) is a genuine path traversal — calling with `subfolder = "../../../etc"` leaks directory listings outside the brain. Requires a 2-line fix.
3. No SQL injection vulnerabilities exist — all queries consistently parameterized throughout the codebase.
4. PII routing gap in `sb_person_context` (returns raw body without Ollama filter) is a design inconsistency, not an exploitable vulnerability. Documented but not elevated.
5. S-05 (no auth on API) confirmed as accepted risk — localhost-only binding is the mitigation.

## Deviations from Plan

None — plan executed exactly as written. The pre-identified S-01 through S-06 items were all confirmed or evaluated with rationale provided for each.

## Self-Check

File created: YES — `.planning/phases/39-codebase-review/39-findings-security.md` exists
Contains SEC- findings: YES — 28 references to SEC- identifiers
Pre-identified items S-01 through S-06: ALL addressed in findings document

Note: The findings file was committed by parallel agent 39-05 (running concurrently). Content is identical — no duplication or conflict.
