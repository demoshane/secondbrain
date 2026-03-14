---
plan: 04-10
status: complete
completed: 2026-03-14
---

# Plan 04-10 Summary: Fix multi-file watcher + post-commit stdin

## What was built

Fixed two independent bugs: (1) watcher silently dropped all but the first file in a multi-file drop; (2) post-commit hook always skipped the brain link prompt because git redirects hook stdin to /dev/null.

## Commits

- `6b36995` feat(04-10): redesign FilesDropHandler to batch all pending files
- `15a2f2e` feat(04-10): fix post-commit hook stdin and pre-commit guard

## Key files

- `engine/watcher.py` — `FilesDropHandler` redesigned with shared `_batch_timer` and `_pending_paths` set; all files dropped within `DEBOUNCE_SECONDS` collected and processed as one batch; rate limiter gates batches not individual files; rate-limited batches retry after window expires
- `engine/hooks/post_commit.py` — all `git` commands now use `-C $SB_PROJECT_DIR` so they target the committed project, not the brain repo
- `.githooks/post-commit` — shell hook cds to brain repo before `uv run` (venv resolution); passes original project dir via `SB_PROJECT_DIR`; stdin remains attached to terminal (not /dev/null)
- `.githooks/pre-commit` — exits 0 silently when no `.pre-commit-config.yaml` exists
- `tests/test_watcher.py` — tests for batch collection, rate-limit retry, concurrent drops

## Decisions

- Per-path timers replaced with single shared batch timer to avoid N-fire problem
- Rate limiter retry uses `_window` delay to match existing `RateLimiter` contract
- `threading.Lock` added for safe concurrent `on_created` + timer callbacks
- Pre-commit guard added to prevent failures in repos without pre-commit config

## Self-Check: PASSED

All must-haves verified:
- ✓ Dropping multiple files triggers capture for ALL files (batch processing)
- ✓ Rate limiting still applies per batch window
- ✓ Post-commit hook presents brain link prompt in interactive terminal session
