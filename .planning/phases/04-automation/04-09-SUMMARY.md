---
plan: 04-09
status: complete
completed: 2026-03-14
---

# Plan 04-09 Summary: Wire RAG into capture pipeline

## What was built

Wired `engine/rag.py` (previously dead code) into the capture pipeline so AI follow-up questions receive relevant existing notes as context.

## Commits

- `a211a9e` feat(04-09): add conn param to ask_followup_questions and wire augment_prompt
- `4354faa` feat(04-08): create 5 skeleton template files *(Task 2 included — conn moved earlier in capture.py)*

## Key files

- `engine/ai.py` — `ask_followup_questions()` gains `conn=None` parameter; calls `augment_prompt(title, conn)` when conn provided
- `engine/capture.py` — `conn = get_connection()` moved before `ask_followup_questions()` call so conn is available
- `tests/test_rag.py` — integration tests confirming wiring: conn wired path and conn=None fallback

## Decisions

- `conn` parameter is optional (`conn=None`) for backwards compatibility
- `augment_prompt` returns title unchanged when no FTS5 matches, so no empty context block is injected
- Task 2 (moving conn in capture.py) was completed by 04-08 agent as a side effect of editing the same file

## Self-Check: PASSED

All must-haves verified:
- ✓ `ask_followup_questions()` receives `conn` parameter
- ✓ `augment_prompt(title, conn)` called instead of raw title
- ✓ `conn` created before `ask_followup_questions()` in capture.py main()
- ✓ RAG wiring in place (FTS5 context injected when results exist)
