#!/usr/bin/env bash
# extract-claude-auth.sh — runs on HOST before container starts (initializeCommand)
#
# WHAT THIS DOES:
#   Reads your Claude Code login credentials from macOS Keychain and writes
#   them to a local config file so the devcontainer can authenticate without
#   requiring a browser-based OAuth flow (which doesn't work in containers).
#
# SECURITY:
#   - The extracted file is written to ~/.config/second-brain/claude-oauth.json
#   - It has chmod 600 (owner-read only) — same security as your .env.host
#   - It contains OAuth tokens, NOT your password or API key
#   - The file is never committed to git (it lives outside the repo)
#   - Inside the container it's copied to ~/.claude/.credentials.json
#
# If you see a macOS Keychain access prompt, that's this script reading
# your Claude Code credentials. It's safe to allow.
set -euo pipefail

CONFIG_DIR="$HOME/.config/second-brain"
AUTH_FILE="$CONFIG_DIR/claude-oauth.json"
ENV_FILE="$CONFIG_DIR/.env.host"

mkdir -p "$CONFIG_DIR"

# Ensure .env.host exists (bind mount fails if missing)
if [ ! -f "$ENV_FILE" ]; then
    echo "# Created automatically — add environment variables as needed" > "$ENV_FILE"
    echo "  ✓ Created empty $ENV_FILE"
fi

# Extract Claude Code credentials from macOS Keychain
if command -v security &>/dev/null; then
    echo "  ℹ Reading Claude Code credentials from macOS Keychain..."
    echo "    (You may see a Keychain access prompt — this is expected and safe to allow)"
    CREDS=$(security find-generic-password -s 'Claude Code-credentials' -w 2>/dev/null || true)
    if [ -n "$CREDS" ]; then
        echo "$CREDS" > "$AUTH_FILE"
        chmod 600 "$AUTH_FILE"
        echo "  ✓ Credentials extracted → $AUTH_FILE (chmod 600)"
    else
        # Create empty file so bind mount doesn't fail
        echo '{}' > "$AUTH_FILE"
        chmod 600 "$AUTH_FILE"
        echo "  ⚠ No Claude Code credentials in Keychain"
        echo "    Run 'claude' on your host first to login, then rebuild the container"
    fi
else
    # Non-macOS host — create empty file so bind mount doesn't fail
    echo '{}' > "$AUTH_FILE"
    chmod 600 "$AUTH_FILE"
    echo "  ⚠ Not on macOS — Keychain extraction skipped"
    echo "    You'll need to run '/login' manually inside the container"
fi
