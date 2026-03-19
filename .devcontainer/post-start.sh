#!/usr/bin/env bash
# post-start.sh — runs inside container on every start
set -euo pipefail

# Fix brain-index volume ownership
sudo chown vscode:vscode /workspace/brain-index

# Copy host .claude.json (onboarding state, settings)
cp /home/vscode/.claude-auth-host/.claude.json /home/vscode/.claude.json 2>/dev/null || true

# Install Claude Code credentials from Keychain-extracted OAuth tokens
if [ -f /home/vscode/.claude-oauth.json ]; then
    CONTENT=$(cat /home/vscode/.claude-oauth.json 2>/dev/null || true)
    if [ -n "$CONTENT" ] && [ "$CONTENT" != "{}" ]; then
        mkdir -p /home/vscode/.claude
        cp /home/vscode/.claude-oauth.json /home/vscode/.claude/.credentials.json
        chmod 600 /home/vscode/.claude/.credentials.json
        echo "✓ Claude Code credentials installed"
    fi
fi

# Symlink host macOS path so hardcoded paths in ~/.claude/settings.json resolve
# (settings.json contains absolute /Users/<name>/.claude/hooks/... paths)
HOST_USER_DIR=$(sed -n 's|.*"/Users/\([^/]*\)/\.claude/.*|\1|p' /home/vscode/.claude/settings.json 2>/dev/null | head -1 || true)
if [ -n "$HOST_USER_DIR" ]; then
    sudo mkdir -p "/Users/$HOST_USER_DIR"
    sudo ln -sfn /home/vscode/.claude "/Users/$HOST_USER_DIR/.claude"
fi
