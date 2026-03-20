---
status: complete
phase: 04-automation
source: [04-01-SUMMARY.md, 04-02-SUMMARY.md, 04-03-SUMMARY.md, 04-04-SUMMARY.md, 04-05-SUMMARY.md]
started: 2026-03-14T00:00:00Z
updated: 2026-03-15T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Backlinks on capture
expected: Capturing a meeting note with `--people "Alice Smith"` automatically creates/updates alice-smith.md in the people/ directory, appending a backlink [[path/to/meeting-note]] to her profile.
result: pass

### 2. Orphan check command
expected: Running `sb-check-links` scans all notes and reports any backlink entries that point to files that no longer exist. Output is a count (and list) of orphaned links, or "0 orphans" if all links resolve.
result: pass

### 3. People search returns cross-type results
expected: Running `sb-search --type people "Alice"` returns Alice's people profile AND lists any meeting notes, coding notes, or other note types that reference her name or contain a backlink to her profile.
result: pass

### 4. RAG-lite context injection (debug output)
expected: When `ask_followup_questions()` is called during a capture, passing `--debug` or checking the prompt shows that relevant previously-captured notes are prepended as a `RETRIEVED CONTEXT` block before the question prompt. If no relevant notes exist, the prompt is unchanged.
result: pass

### 5. Templates exist for all work types
expected: The directory `brain/.meta/templates/` contains at minimum: `people.md`, `meeting.md`, `projects.md`, `coding.md`, `strategy.md`. Each file has a meaningful skeleton (not empty) with type-appropriate sections.
result: pass

### 6. New note types work in sb-capture
expected: Running `sb-capture --type projects ...` and `sb-capture --type personal ...` succeed without error. Previously broken: `--type idea` now correctly writes to `brain/ideas/` (not `brain/idea/`).
result: pass

### 7. File watcher triggers on file drop
expected: Starting `sb-watch` and dropping any file into `~/SecondBrain/files/` triggers a categorization prompt within ~10 seconds. Dropping 20 files rapidly produces at most one prompt per 5-second window (rate-limiting / debounce).
result: pass

### 8. Git post-commit hook fires on commit
expected: After installing `.githooks/post-commit` (via `git config core.hooksPath .githooks` in a project), making a commit triggers the hook. The hook offers an AI-generated summary and, if accepted, creates a brain entry linked to the relevant project note.
result: pass

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
