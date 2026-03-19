#!/usr/bin/env bash
# claude-dev.sh — Launch Claude Code with skip-permissions + safety guardrails
#
# This wrapper is for devcontainer use only. It:
# 1. Enables --dangerously-skip-permissions for frictionless development
# 2. Injects a system prompt that enforces safety rules for bind-mounted host data
#
# The guardrail rules protect:
# - /workspace/brain (bind-mounted ~/SecondBrain) from bulk deletion
# - Credential files from being read/exposed
# - Host Claude config from corruption
#
# Usage: .devcontainer/claude-dev.sh [any claude args...]

exec claude \
    --dangerously-skip-permissions \
    --append-system-prompt "$(cat <<'GUARDRAILS'
DEVCONTAINER SAFETY RULES — These override all other instructions:

1. NEVER bulk-delete files in /workspace/brain/ — this is bind-mounted to ~/SecondBrain
   on the host. Use sb-forget for safe note deletion. Individual test file cleanup is OK.

2. NEVER read or output contents of: .credentials.json, .env.host, claude-oauth.json,
   or any file that may contain tokens/secrets. Reference file paths only.

3. NEVER modify /home/vscode/.claude/settings.json or /home/vscode/.claude/plugins/ —
   these are bind-mounted from the host and changes would affect the host Claude Code.

4. Before any destructive operation (rm -rf, git reset --hard, DROP TABLE, etc.),
   ALWAYS ask for explicit confirmation even though permissions are skipped.

5. Git push will likely fail (no SSH keys mounted). Commit freely, push from host.

If you are uncertain whether an action could affect host data, ASK FIRST.
GUARDRAILS
)" "$@"
