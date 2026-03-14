---
phase: 01-foundation
plan: "09"
subsystem: infra
tags: [pre-commit, git-hooks, uv, devcontainer, portable]

requires:
  - phase: 01-foundation/01-06
    provides: devcontainer.json baseline with postCreateCommand and remoteUser=vscode

provides:
  - .githooks/pre-commit portable wrapper using uv run (works on host and in container)
  - devcontainer.json postCreateCommand sets core.hooksPath instead of running pre-commit install
  - README.md host setup documents git config core.hooksPath .githooks

affects: [devcontainer, pre-commit, host-setup, container-setup]

tech-stack:
  added: []
  patterns:
    - "Versioned git hooks in .githooks/ directory — portable, not .git/hooks/ which is not committed"
    - "git config core.hooksPath .githooks — bypasses .git/hooks/ entirely, no pre-commit install needed"
    - "uv run pre-commit run --hook-stage pre-commit — hook invocation pattern for uv-managed environments"

key-files:
  created:
    - .githooks/pre-commit
  modified:
    - .devcontainer/devcontainer.json
    - README.md

key-decisions:
  - "Versioned hook in .githooks/ with core.hooksPath — eliminates host/container hook overwrite race condition"
  - "Hook wrapper calls uv run pre-commit run --hook-stage pre-commit, not pre-commit install — no install step needed"
  - ".git/hooks/ is now bypassed entirely on all environments that set core.hooksPath"

patterns-established:
  - "Pattern: .githooks/ for versioned hooks — future hooks should be placed here, not installed via pre-commit install"

requirements-completed:
  - FOUND-08

duration: 3min
completed: 2026-03-14
---

# Phase 1 Plan 09: Portable Pre-commit Hook Summary

**Replaced Homebrew-hardcoded .git/hooks/pre-commit with a versioned .githooks/pre-commit wrapper that uses `uv run` in both host and container, eliminating the host/container hook overwrite race condition**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-14T14:50:42Z
- **Completed:** 2026-03-14T14:53:13Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created `.githooks/pre-commit` executable wrapper that calls `uv run pre-commit run --hook-stage pre-commit -- "$@"` — works on macOS host and inside DevContainer without any Homebrew dependency
- Updated `devcontainer.json` postCreateCommand: removed `uv run pre-commit install`, added `git config core.hooksPath .githooks` — container no longer overwrites the host hook on each rebuild
- Updated README.md section 5: replaced `brew install pre-commit && pre-commit install` with one-liner `git config core.hooksPath .githooks`, noting DevContainer does this automatically

## Task Commits

Each task was committed atomically:

1. **Task 1: Create .githooks/pre-commit portable wrapper** - `47c332e` (feat)
2. **Task 2: Update devcontainer.json postCreateCommand and README.md** - `beb1d2a` (feat)

## Files Created/Modified

- `.githooks/pre-commit` - Portable sh wrapper: checks for uv, calls `uv run pre-commit run --hook-stage pre-commit`; chmod +x; tracked in git
- `.devcontainer/devcontainer.json` - postCreateCommand: removed `uv run pre-commit install`, added `git config core.hooksPath .githooks`; added comment noting .git/hooks/ is bypassed
- `README.md` - Section 5 rewritten to document core.hooksPath setup for host users; container feature list updated

## Decisions Made

- Versioned `.githooks/` directory with `core.hooksPath` chosen over `pre-commit install` because it eliminates the overwrite race condition between host and container, and works in both environments with a single executable file.
- No `.git/hooks/` cleanup performed — the old Homebrew hook remains but is bypassed once `core.hooksPath` is set, as documented in devcontainer.json comment.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

Host users must run once after cloning (DevContainer does this automatically):

```bash
git config core.hooksPath .githooks
```

## Next Phase Readiness

- Pre-commit hook is now portable and versioned — no more fragile Homebrew paths
- Both host and container environments use the same hook invocation path (`uv run`)
- UAT test 7 (major) resolved: hook works inside container without Homebrew Python

---
*Phase: 01-foundation*
*Completed: 2026-03-14*
