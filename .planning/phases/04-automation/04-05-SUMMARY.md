---
phase: 04-automation
plan: "05"
subsystem: automation
tags: [git-hooks, subprocess, tty, ai-summarization, cap-05]

requires:
  - phase: 04-00
    provides: stub files engine/hooks/post_commit.py and tests/test_hooks.py
  - phase: 03-ai-layer
    provides: engine/router.get_adapter, ClaudeAdapter, engine/paths.CONFIG_PATH

provides:
  - engine/hooks/post_commit.py — get_commit_info() with initial-commit fallback, main() with TTY guard
  - .githooks/post-commit — shell wrapper delegating to engine.hooks.post_commit via uv or python
  - tests/test_hooks.py — 3 real unit tests replacing xfail stubs

affects: [phase-05-ui, any phase using git automation]

tech-stack:
  added: []
  patterns:
    - "subprocess.run per-call with capture_output=True, text=True, timeout=10"
    - "Deferred import inside main() for engine.router — patch engine.router.get_adapter in tests"
    - "TTY guard: sys.stdin.isatty() before any input() call"
    - "Fallback chain: git diff HEAD~1 returncode 128 -> git show --stat HEAD"

key-files:
  created:
    - .githooks/post-commit
  modified:
    - engine/hooks/post_commit.py
    - tests/test_hooks.py

key-decisions:
  - "patch engine.router.get_adapter (module ref) not engine.hooks.post_commit.get_adapter — deferred import means get_adapter is not a module-level attribute of post_commit"

patterns-established:
  - "Post-commit hook: TTY guard before prompt, print to stderr on non-interactive skip"
  - "Initial commit fallback: check returncode == 128 on git diff HEAD~1, fallback to git show --stat HEAD"

requirements-completed: [CAP-05]

duration: 8min
completed: 2026-03-14
---

# Phase 04 Plan 05: Post-Commit Hook Summary

**git post-commit hook with AI summarization via ClaudeAdapter, TTY guard, and initial-commit fallback — CAP-05 fulfilled**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-14T18:22:00Z
- **Completed:** 2026-03-14T18:30:00Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments

- Implemented `get_commit_info()` extracting commit subject, file stat, and repo name via subprocess, with fallback to `git show --stat HEAD` for initial commits (returncode 128)
- Implemented `main()` with TTY guard — prints to stderr and skips prompt when `sys.stdin.isatty()` returns False
- Created `.githooks/post-commit` executable shell wrapper delegating to `engine.hooks.post_commit` via `uv run --no-project python -m` or bare python
- Replaced all 3 xfail stub tests with real unit tests; 79 tests pass in full suite

## Task Commits

Note: Task 1 implementation was committed as part of the 04-04 execution session (files were staged together with watcher files). The 04-05 plan verifies the implementation is correct and tests pass.

1. **Task 1: Implement engine/hooks/post_commit.py and .githooks/post-commit** - `249c1fc` (feat — committed in 04-04 session)

## Files Created/Modified

- `engine/hooks/post_commit.py` — full implementation replacing stub: get_commit_info() with HEAD~1 fallback, main() with TTY guard and brain link prompt
- `.githooks/post-commit` — sh wrapper: `uv run --no-project python -m engine.hooks.post_commit "$@"` with uv/python fallback
- `tests/test_hooks.py` — 3 passing unit tests: get_commit_info mock, initial commit fallback, non-interactive TTY skip

## Decisions Made

- Patch `engine.router.get_adapter` (module-level ref) rather than `engine.hooks.post_commit.get_adapter` — the deferred import inside `main()` means `get_adapter` is not a module-level attribute of the hooks module; patching the router module's attribute is the correct intercept point (follows Phase 3 pattern from STATE.md)

## Deviations from Plan

None — plan executed exactly as written. The implementation was already in HEAD from the 04-04 execution session (files staged and committed together). All verification criteria confirmed passing.

## Issues Encountered

- Pre-commit hook (detect-secrets) updated `.secrets.baseline` during first commit attempt, causing a "Failed" exit code. The implementation files were already in HEAD from the prior 04-04 session — this was determined by checking `git log -- engine/hooks/post_commit.py`.

## Next Phase Readiness

- CAP-05 complete: post-commit hook is implemented and tested
- `.githooks/post-commit` is executable and uses the same `.githooks/` pattern as the pre-commit hook
- Users install per-project via `git config core.hooksPath /path/to/brain/.githooks`
- Full suite: 79 passed, 4 skipped, 1 xpassed

---
*Phase: 04-automation*
*Completed: 2026-03-14*
