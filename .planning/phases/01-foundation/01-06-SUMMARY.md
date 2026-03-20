---
phase: 01-foundation
plan: "06"
subsystem: infra
tags: [devcontainer, docker, sqlite, pre-commit, detect-secrets, bootstrap]

requires:
  - phase: 01-01
    provides: devcontainer config and Dockerfile
  - phase: 01-02
    provides: pre-commit and detect-secrets config
  - phase: 01-03
    provides: engine/init_brain.py and db schema
  - phase: 01-04
    provides: engine/reindex.py and sb-reindex
  - phase: 01-05
    provides: scripts/bootstrap.py environment validator

provides:
  - Verified DevContainer opens on macOS with vscode user (UID 1000)
  - Verified ~/SecondBrain bind-mounted at /workspace/brain with correct ownership
  - Verified /sb-init creates 9 subdirs + SQLite schema + .vscode/settings.json
  - Verified /sb-reindex runs clean on empty brain (0 notes indexed)
  - Verified bind mount: file written in container visible on host with correct ownership
  - Verified pre-commit hook runs and blocks secrets (RSA private key)
  - Fixed 4 infrastructure bugs discovered during manual verification

affects: [phase-02, phase-03]

tech-stack:
  added: []
  patterns:
    - "postStartCommand: sudo chown to fix named volume ownership for non-root user"
    - "sudo npm install -g for global npm packages in non-root devcontainer"
    - "~/.gitconfig bind-mounted from host for git identity in container"

key-files:
  created: []
  modified:
    - scripts/bootstrap.py
    - .devcontainer/devcontainer.json
    - pyproject.toml
    - .secrets.baseline

key-decisions:
  - "Container detection: check REMOTE_CONTAINERS env var + /workspace dir, not just /.dockerenv (absent in some DevContainer builds)"
  - "Named volume /workspace/brain-index owned by root by default — fix via postStartCommand: sudo chown"
  - "hatchling requires explicit packages list — added [tool.hatch.build.targets.wheel] packages = ['engine', 'scripts']"
  - "~/.gitconfig must be explicitly mounted; not inherited automatically by DevContainers"
  - "detect-secrets gibberish_detector not available in container — regenerate .secrets.baseline inside container"
  - "detect-secrets has no Anthropic API key plugin; hook protects via baseline diff, not pattern matching"

patterns-established:
  - "Verify infrastructure with real container, not just unit tests — 4 bugs found that tests couldn't catch"

requirements-completed:
  - FOUND-01
  - FOUND-02
  - FOUND-11

duration: 90min
completed: 2026-03-14
---

# Phase 1: Foundation — Manual Verification Summary

**DevContainer opens on macOS, all Phase 1 success criteria confirmed; 4 infrastructure bugs found and fixed during end-to-end verification.**

## Performance

- **Duration:** ~90 min
- **Completed:** 2026-03-14
- **Tasks:** 2 (automated tests + human checkpoint)
- **Files modified:** 4

## Accomplishments

All 5 Phase 1 roadmap success criteria confirmed:

1. **bootstrap.py --dev** reports all checks green inside the container
2. **Pre-commit hook** blocks secrets (RSA private key detected and commit rejected)
3. **.env.host** not in git, bind-mounted from `~/.config/second-brain/.env.host` → `/workspace/.env.host`
4. **/sb-init** creates 9 subdirs + SQLite schema + `.vscode/settings.json`; **/sb-reindex** indexes 0 notes on empty brain
5. **Bind mount ownership** correct — file written at `/workspace/brain/test.md` visible on host at `~/SecondBrain/test.md` owned by host user

## Bugs Fixed

| # | Bug | Fix |
|---|-----|-----|
| 1 | `/.dockerenv` absent in this DevContainer build → bootstrap used host paths inside container | Check `REMOTE_CONTAINERS` env var + `/workspace` dir existence |
| 2 | `uv pip install -e '.[dev]'` failed — hatchling couldn't find `second_brain/` package | Added `[tool.hatch.build.targets.wheel] packages = ["engine", "scripts"]` to pyproject.toml |
| 3 | Named volume `/workspace/brain-index` owned by root → SQLite `unable to open database file` | Added `postStartCommand: sudo chown vscode:vscode /workspace/brain-index` |
| 4 | `npm install -g @anthropic-ai/claude-code` failed (EACCES) | Changed to `sudo npm install -g` in postCreateCommand |

## Known Limitations

- **detect-secrets has no Anthropic API key plugin** — `sk-ant-api03-*` keys are not caught by pattern matching. Protection relies on baseline diff for high-entropy strings and other known patterns. Custom regex plugin needed for full Anthropic key coverage.
- **Windows WSL2 testing deferred** — `${localEnv:HOME}` may resolve to Windows path; documented in devcontainer.json comment.
