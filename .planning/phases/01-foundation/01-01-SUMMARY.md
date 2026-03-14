---
phase: 01-foundation
plan: "01"
subsystem: infra
tags: [devcontainer, docker, vscode, python, nodejs, security, gitignore]

# Dependency graph
requires:
  - phase: 01-foundation/01-00
    provides: pyproject.toml scaffold, test infrastructure, uv setup
provides:
  - Dockerfile with non-root vscode user (UID 1000) and passwordless sudo
  - devcontainer.json with remoteUser=vscode, brain bind mount, SQLite named volume, .env.host injection from outside Drive
  - .gitignore excluding secrets (.env.host, *.env) and artifacts (*.db, __pycache__, .venv/)
  - .env.host.example template committed with placeholder values
  - TDD tests verifying devcontainer config and gitignore correctness
affects: [all phases — devcontainer is the runtime environment for all development]

# Tech tracking
tech-stack:
  added: [python:3.12-slim, nodejs-22, uv, pytest]
  patterns: [non-root devcontainer user pattern, secrets-outside-Drive pattern, TDD for config file verification]

key-files:
  created:
    - .devcontainer/Dockerfile
    - .devcontainer/devcontainer.json
    - .gitignore
    - .env.host.example
    - tests/test_devcontainer.py
    - tests/test_gitignore.py
  modified: []

key-decisions:
  - "remoteUser=vscode (UID 1000) — not root — prevents Drive sync permission failures on bind mounts"
  - ".env.host sourced from ~/.config/second-brain/ (outside ~/SecondBrain Drive folder) — never Drive-synced"
  - "SQLite uses named Docker volume brain-index-data (not bind mount) — index is rebuildable, never synced"
  - "Windows WSL2 HOME expansion issue documented in devcontainer.json comment (runtime warning in bootstrap.py)"

patterns-established:
  - "Config-as-code TDD: parse JSON/text config files in tests to assert structural invariants"
  - "Secrets separation: .env.host lives at ~/.config/second-brain/ — outside Drive, outside git"

requirements-completed: [FOUND-01, FOUND-02, FOUND-09, FOUND-12]

# Metrics
duration: 2min
completed: 2026-03-14
---

# Phase 1 Plan 01: Devcontainer Security Fix Summary

**Devcontainer rewritten to run as non-root vscode user (UID 1000) with brain bind mount, SQLite named volume, and .env.host injection from outside the Drive-synced folder**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-14T12:41:05Z
- **Completed:** 2026-03-14T12:43:11Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Dockerfile creates vscode user (UID 1000) with passwordless sudo; final USER directive is non-root
- devcontainer.json rewrites all mounts to /home/vscode paths and injects .env.host from ~/.config/second-brain/ (outside ~/SecondBrain Drive folder)
- .gitignore excludes .env.host, *.env, *.db, __pycache__/, .venv/ — secrets never land in git
- TDD test suite (8 tests) verifies all structural invariants in config files

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix Dockerfile to create vscode user (UID 1000)** - `e41d246` (feat)
2. **Task 2: Rewrite devcontainer.json with correct mounts and fill tests** - `3aa1d2c` (feat)

**Plan metadata:** (docs commit — see below)

_Note: TDD tasks have inline test + implementation commits (RED integrated into task commit as tests were written before fixing)_

## Files Created/Modified

- `.devcontainer/Dockerfile` - Python 3.12-slim + Node 22 + uv; vscode user (UID 1000) with sudo; final USER $USERNAME
- `.devcontainer/devcontainer.json` - remoteUser=vscode; brain bind mount from ~/SecondBrain; SQLite named volume; .env.host from ~/.config/second-brain/; Claude config mounts targeting /home/vscode
- `.gitignore` - Excludes .env.host, *.env, *.db, __pycache__/, .venv/, dist/, build/
- `.env.host.example` - Template with ANTHROPIC_API_KEY placeholder; instructions to copy to ~/.config/second-brain/
- `tests/test_devcontainer.py` - 6 tests: Dockerfile vscode user, devcontainer remoteUser, brain mount, env_host mount source path
- `tests/test_gitignore.py` - 2 tests: .env.host and *.db entries present in .gitignore

## Decisions Made

- `remoteUser` changed from `root` to `vscode` — root causes bind-mount files to be owned by root on host, breaking Drive sync
- `.env.host` sourced from `~/.config/second-brain/` not `~/SecondBrain/` — Drive-syncing secrets is a critical security violation
- Claude config mounts target `/home/vscode/` not `/root/` — consistent with non-root user
- `runArgs --env-file` hard-fails if file missing — documented in devcontainer.json comments and .env.host.example

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

Before opening this devcontainer, create `~/.config/second-brain/.env.host`:

```bash
mkdir -p ~/.config/second-brain
cp .env.host.example ~/.config/second-brain/.env.host
# Edit the file and fill in your real ANTHROPIC_API_KEY
```

`runArgs --env-file` will hard-fail if this file does not exist.

## Next Phase Readiness

- Devcontainer security baseline complete — all file ownership will be vscode (UID 1000), safe for Drive sync
- Brain bind mount and SQLite volume configured — ready for Phase 2 (index build)
- Secrets pattern established — no secrets ever in git or Drive

---
*Phase: 01-foundation*
*Completed: 2026-03-14*
