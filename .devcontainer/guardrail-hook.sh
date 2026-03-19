#!/usr/bin/env bash
# guardrail-hook.sh — PreToolUse safety hook for devcontainer
#
# Runs even with --dangerously-skip-permissions. Blocks destructive operations
# that could damage bind-mounted host data (brain notes, Claude config).
#
# Exit 0 = allow, Exit 2 = block with message
set -euo pipefail

TOOL_NAME="${CLAUDE_TOOL_NAME:-}"
TOOL_INPUT="${CLAUDE_TOOL_INPUT:-}"

# ── Block destructive operations on brain data ─────────────────────────────
if [ "$TOOL_NAME" = "Bash" ]; then
    # Block rm/rmdir targeting brain directory
    if echo "$TOOL_INPUT" | grep -qE '(rm|rmdir)\s.*(/workspace/brain|/workspace/brain/)'; then
        echo '{"decision": "block", "reason": "BLOCKED: Cannot delete files in /workspace/brain — this is bind-mounted to ~/SecondBrain on the host. Use sb-forget for safe note deletion."}'
        exit 2
    fi

    # Block commands that could wipe brain data
    if echo "$TOOL_INPUT" | grep -qE '(rm\s+-rf?\s+/workspace/brain|find\s+/workspace/brain.*-delete)'; then
        echo '{"decision": "block", "reason": "BLOCKED: Destructive operation on brain data. /workspace/brain is bind-mounted to ~/SecondBrain."}'
        exit 2
    fi

    # Block reading secret files
    if echo "$TOOL_INPUT" | grep -qE '(cat|head|tail|less|more|bat)\s.*(\.credentials\.json|\.env\.host|claude-oauth\.json)'; then
        echo '{"decision": "block", "reason": "BLOCKED: Cannot read credential/secret files. Reference the file path only."}'
        exit 2
    fi

    # Block modifications to host Claude config
    if echo "$TOOL_INPUT" | grep -qE '(rm|mv|cp|sed|tee|>)\s.*/home/vscode/\.claude/(settings\.json|plugins/)'; then
        echo '{"decision": "block", "reason": "BLOCKED: Cannot modify ~/.claude/settings.json or plugins — bind-mounted from host."}'
        exit 2
    fi

    # Block git push (code changes should be reviewed on host first)
    if echo "$TOOL_INPUT" | grep -qE 'git\s+push'; then
        echo '{"decision": "block", "reason": "BLOCKED: git push not allowed from devcontainer. Push from host after review."}'
        exit 2
    fi
fi

# ── Block writing to brain directory directly (use capture API) ────────────
if [ "$TOOL_NAME" = "Write" ] || [ "$TOOL_NAME" = "Edit" ]; then
    if echo "$TOOL_INPUT" | grep -qE '/workspace/brain/'; then
        echo '{"decision": "block", "reason": "BLOCKED: Cannot write directly to /workspace/brain — use sb-capture or the MCP tools for note operations."}'
        exit 2
    fi
fi
