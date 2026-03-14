---
phase: 03-ai-layer
plan: "03"
subsystem: ai-layer
tags: [ai, capture, proactive-questions, gdpr, tdd]
dependency_graph:
  requires: [03-02]
  provides: [engine/ai.py, updated capture.py main()]
  affects: [capture pipeline, AI-01, AI-10, CAP-06]
tech_stack:
  added: []
  patterns: [module-ref import for mock-interceptable patching, fallback questions on AI failure]
key_files:
  created:
    - engine/ai.py
  modified:
    - engine/capture.py
    - engine/paths.py
decisions:
  - "Import engine.router as module ref (not from-import) so engine.router.get_adapter patches intercept correctly in tests"
  - "CONFIG_PATH added to engine/paths.py as alias for CONFIG_FILE — same value, explicit name used by capture.py and ai.py"
  - "ask_followup_questions returns FALLBACK_QUESTIONS on any exception (never raises)"
  - "update_memory uses shutil.which check before subprocess call — explicit error for missing claude CLI"
metrics:
  duration_minutes: 3
  completed_date: "2026-03-14"
  tasks_completed: 2
  files_changed: 3
---

# Phase 3 Plan 03: AI Proactive Questions Layer Summary

**One-liner:** Proactive capture enrichment via content-type-aware questions (AI-01) with fallback-safe adapter calls and AI-10 prompt-injection protection.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | engine/ai.py — ask_followup_questions and update_memory | 68d5317 | engine/ai.py |
| 2 | Wire proactive questions into capture.py main() | 2e8645e | engine/capture.py, engine/paths.py |

## What Was Built

### engine/ai.py

- `QUESTION_SYSTEM_PROMPTS`: 6 static system prompts (meeting, idea, coding, people, strategy, note) — never include user content (AI-10)
- `FALLBACK_QUESTIONS`: 2 hardcoded questions per content type, returned if AI fails or returns < 2 questions
- `ask_followup_questions(note_type, title, sensitivity, config_path)`: calls `engine.router.get_adapter()`, generates questions, parses numbered/dashed list, truncates to 3, falls back if < 2 parsed
- `update_memory(note_type, summary, config_path)`: uses `ClaudeAdapter` subprocess with `--allowedTools Write,Read` (CAP-06); logs only `type(e).__name__` on failure (GDPR-05)

### engine/capture.py main()

- Added `classify(args.sensitivity, args.body)` call before note write (AI-02 enforcement point)
- Added `ask_followup_questions()` call with try/except guard (AI-01; Pitfall 5 prevention)
- User answers printed and collected interactively; non-empty answers appended to note body as markdown
- `capture_note()` signature unchanged — all 5 existing capture tests pass

### engine/paths.py

- Added `CONFIG_PATH = CONFIG_FILE` alias for explicit reference in capture and ai modules

## Success Criteria Verification

- [x] engine/ai.py exists with ask_followup_questions() and update_memory()
- [x] QUESTION_SYSTEM_PROMPTS has entries for all 6 content types
- [x] AI failure returns fallback questions, never raises
- [x] capture.py main() calls ask_followup_questions before write
- [x] capture_note() signature unchanged (existing tests unbroken)
- [x] AI-10: system_prompt contains no user-controlled content (test_no_user_content_in_system_prompt passes)

## Test Results

```
25 passed in 0.91s
tests/test_classifier.py  5/5
tests/test_adapters.py    5/5
tests/test_router.py      5/5
tests/test_ai.py          5/5
tests/test_capture.py     5/5
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed mock interception for engine.router.get_adapter patch**

- **Found during:** Task 1 GREEN phase
- **Issue:** `from engine.router import get_adapter` binds the name in `engine.ai` namespace; `patch("engine.router.get_adapter")` doesn't intercept calls to the local binding
- **Fix:** Changed to `import engine.router as _router` and call `_router.get_adapter(...)` — module attribute lookup happens at call time, so the patch intercepts correctly
- **Files modified:** engine/ai.py
- **Commit:** 68d5317

## Self-Check: PASSED

- engine/ai.py: FOUND
- engine/capture.py: FOUND
- engine/paths.py: FOUND
- commit 68d5317: FOUND
- commit 2e8645e: FOUND
