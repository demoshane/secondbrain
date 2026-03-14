# Phase 1: Foundation - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Secure, reproducible DevContainer verified on macOS and Windows. Secrets never touch git or Drive. Brain folder structure exists. `/sb-init` and `/sb-reindex` are operational. Pre-commit hook blocks secret commits. No user-facing features or AI behavior — infrastructure only.

</domain>

<decisions>
## Implementation Decisions

### /sb-init behavior
- Validate Drive mount is active and writable BEFORE creating any folders (FOUND-05)
- Report what already exists vs. what was created — not silent, not erroring
- Skip SQLite schema creation if tables already exist (idempotent re-runs are safe)
- `--force` flag recreates folders (mkdir -p, no-op if exists) but preserves existing notes
- Schema reinit only if `--reset-db` is passed separately (explicit, destructive operation)
- No `--force` flag needed for normal re-runs — idempotency handles it

### remoteUser
- Must be `vscode` (not root) — current devcontainer.json has `root`, must be corrected
- Consistent user everywhere: Dockerfile, devcontainer.json, bind-mount targets

### Claude's Discretion
- bootstrap.py output format and verbosity (fail-fast vs. check-all is implementation detail)
- .env.host placement and Drive exclusion method (.gdriveignore or folder placement)
- Pre-commit hook implementation (detect-secrets or custom patterns)
- /sb-init exit codes and exact output formatting

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.devcontainer/Dockerfile`: Python 3.12-slim + SQLite + Node.js + uv — good baseline, no changes needed to tech stack
- `.devcontainer/devcontainer.json`: skeleton exists, needs brain mount, SQLite volume, .env.host injection, remoteUser fix

### Established Patterns
- `${localEnv:HOME}` used for mounts — needs Windows/WSL2 testing (FOUND-02 blocker noted in STATE.md)
- uv for Python package management — use for all Python deps in engine

### Integration Points
- Brain mount: `~/SecondBrain` → `/workspace/brain` (bind mount in devcontainer.json)
- SQLite volume: named Docker volume `brain-index-data` → `/workspace/brain-index`
- `.env.host`: bind-mounted from host, excluded from git (.gitignore) and Drive sync

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-03-14*
