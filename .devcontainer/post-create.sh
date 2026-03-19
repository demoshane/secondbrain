#!/usr/bin/env bash
# post-create.sh — runs once after devcontainer is first built
# Sets up the full development environment.
set -euo pipefail

REPO="$(pwd)"

echo "▶ Installing Claude Code..."
sudo npm install -g @anthropic-ai/claude-code

echo "▶ Installing Python dependencies (editable + dev)..."
uv sync --dev

echo "▶ Installing as uv tool (registers sb-* CLI commands)..."
uv tool install --editable --force "$REPO"

echo "▶ Installing frontend dependencies..."
npm ci --prefix "$REPO/frontend"

echo "▶ Building frontend bundle..."
npm run build --prefix "$REPO/frontend"

echo "▶ Configuring git hooks..."
git config core.hooksPath .githooks

echo "▶ Setting up claude-dev alias..."
echo 'alias claude-dev="/workspace/.devcontainer/claude-dev.sh"' >> /home/vscode/.bashrc

echo "▶ Installing Playwright browsers (optional — GUI testing runs on host)..."
uv run python -m playwright install --with-deps chromium 2>/dev/null \
    || echo "  ⚠ Playwright setup skipped — GUI testing happens on host anyway"

echo "▶ Initialising brain structure..."
uv run sb-init --yes 2>/dev/null || true

echo "▶ Building search index..."
uv run sb-reindex 2>/dev/null || echo "  ⚠ Reindex skipped (brain may be empty)"

echo ""
echo "✓ Devcontainer ready."
echo "  Repo:     $REPO"
echo "  Brain:    $REPO/brain"
echo "  DB index: $REPO/brain-index"
echo ""
echo "  claude-dev    Launch Claude Code with skip-permissions + safety guardrails"
echo "  claude        Launch Claude Code with normal permissions"
echo ""
echo "  Development:  edit code, run pytest, git — all inside container"
echo "  GUI testing:  run deploy pipeline on HOST, test at localhost:37491/ui"
