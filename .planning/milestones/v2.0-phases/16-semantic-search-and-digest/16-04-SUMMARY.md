---
phase: 16-semantic-search-and-digest
plan: "04"
subsystem: digest
tags: [digest, weekly, pii-routing, launchd, sb-read]
dependency_graph:
  requires: [16-03, engine/intelligence.py, engine/paths.py, engine/db.py]
  provides: [engine/digest.py, sb-digest CLI, --digest flag in sb-read, com.secondbrain.digest.plist]
  affects: [engine/read.py, scripts/install_native.py]
tech_stack:
  added: [python-frontmatter (digest file writing)]
  patterns: [ISO week filename (%G-W%V), PII-aware AI routing, idempotent file generation, launchd StartCalendarInterval]
key_files:
  created: [engine/digest.py]
  modified: [engine/read.py, scripts/install_native.py, tests/test_digest.py]
decisions:
  - conn=None guard added to generate_digest() so tests with None conn skip DB queries gracefully
  - TestDigestPIIRouting fixed to use monkeypatch.setattr on engine.intelligence._router and in-memory DB with PII note
  - TestDigestWrite path assertion fixed from (tmp_path/'digests').exists() to result.parent == digests_dir
  - write_digest_plist() wrapped in non-fatal try/except in main() — binary may not be installed yet
metrics:
  duration: 196s
  completed: "2026-03-15"
  tasks: 2
  files_modified: 4
---

# Phase 16 Plan 04: Digest Engine and Weekly Trigger Summary

**One-liner:** Weekly digest engine with PII-aware AI routing, four-section Markdown output, idempotent writes, sb-read --digest flag, and Monday 08:00 launchd trigger.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement engine/digest.py fully | f5ddaaa | engine/digest.py, tests/test_digest.py |
| 2 | Add --digest flag to read.py; digest launchd plist | c8dc37d | engine/read.py, scripts/install_native.py |

## What Was Built

**engine/digest.py** — Full digest generation module:
- `_week_filename()` — ISO week filename using `%G-W%V` (ISO week year, not calendar year)
- `generate_digest(conn, digests_dir)` — idempotent: prints skip message and returns existing path if this week's file exists; otherwise writes YAML frontmatter + four-section Markdown body
- Four sections: Key Themes (AI-generated, PII-aware), Open Actions (from action_items table), Stale Notes (from get_stale_notes()), Captures This Week (notes created >= 7 days ago)
- PII notes routed to Ollama via `_router.get_adapter("pii", CONFIG_PATH)`; non-PII to Claude; AI failure falls back to "Key Themes unavailable." — never blocks file write
- `digest_main()` — CLI entry point; wires to BRAIN_ROOT/.meta/digests/

**engine/read.py** — Added `--digest` flag:
- `_resolve_digest(digests_dir, selector)` — "latest" returns lexicographic max; specific "YYYY-WNN" resolves by name
- `main()` refactored to accept `argv` parameter; `path` arg is now `nargs="?"` so --digest can be used standalone
- Digest files read directly without PII gate (type: digest, not content_sensitivity: pii)
- Empty digests dir prints "No digests found." and exits 0

**scripts/install_native.py** — Added `write_digest_plist()`:
- Writes `com.secondbrain.digest.plist` to `~/Library/LaunchAgents/`
- `StartCalendarInterval: {Weekday: 1, Hour: 8, Minute: 0}` (Monday 08:00)
- Non-fatal guard in `main()`: prints warning if sb-digest binary not in PATH

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TestDigestWrite path assertion**
- **Found during:** Task 1 (RED test run)
- **Issue:** Test asserted `(tmp_path / "digests").exists()` but `generate_digest` was called with `tmp_path` as the digests_dir directly — the subdirectory never gets created
- **Fix:** Changed test to assert `result.parent == digests_dir` and call `generate_digest(None, digests_dir)` with an explicit subdirectory
- **Files modified:** tests/test_digest.py
- **Commit:** f5ddaaa

**2. [Rule 1 - Bug] Fixed TestDigestPIIRouting — mock_router never injected**
- **Found during:** Task 1 (test run)
- **Issue:** Test created a `mock_router` local variable but never patched `engine.intelligence._router`, so the module-level router was used; with `conn=None` no PII notes queried; `mock_router.get_adapter.call_args_list` was always empty; assertion always failed
- **Fix:** Added `monkeypatch.setattr("engine.intelligence._router", mock_router)` and helper `_make_db_with_pii_note()` that creates an in-memory DB with a PII note seeded for today
- **Files modified:** tests/test_digest.py
- **Commit:** f5ddaaa

**3. [Rule 2 - Missing guard] Added conn=None guard in generate_digest()**
- **Found during:** Task 1 — tests pass `conn=None`
- **Issue:** Plan code assumed conn is always a real connection; passing None would crash immediately on `.execute()`
- **Fix:** Wrapped all DB queries in `if conn is not None:` guards so tests with None conn run gracefully (fallback text for all sections)
- **Files modified:** engine/digest.py
- **Commit:** f5ddaaa

## Verification Results

- All 4 TestDigest* classes GREEN: TestDigestWrite, TestDigestIdempotent, TestDigestSections, TestDigestPIIRouting
- TestDigestFlag and TestDigestFlagEmpty GREEN
- All existing test_read.py tests unaffected (11/11 pass)
- Full suite: all pass except pre-existing test_precommit.py::test_blocks_api_key failure (out of scope)
- `from engine.digest import generate_digest, digest_main` — importable OK
- `sb-digest = "engine.digest:digest_main"` registered in pyproject.toml
- `StartCalendarInterval` present in scripts/install_native.py

## Self-Check: PASSED
