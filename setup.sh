#!/usr/bin/env bash
# setup.sh — one-command setup for second-brain on a new machine (macOS host)
#
# Usage:
#   ./setup.sh                # full setup (recommended)
#   ./setup.sh --skip-reindex # skip initial index build (faster, run sb-reindex later)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKIP_REINDEX=false

for arg in "$@"; do
  [[ "$arg" == "--skip-reindex" ]] && SKIP_REINDEX=true
done

# ── helpers ──────────────────────────────────────────────────────────────────
ok()   { printf "  \033[32m✓\033[0m %s\n" "$*"; }
fail() { printf "  \033[31m✗\033[0m %s\n" "$*" >&2; }
step() { printf "\n\033[1m▶ %s\033[0m\n" "$*"; }

# ── 1. Prerequisites ──────────────────────────────────────────────────────────
step "Checking prerequisites"

if ! command -v uv &>/dev/null; then
  fail "uv not found — install it first: https://docs.astral.sh/uv/"
  exit 1
fi
ok "uv $(uv --version)"

if ! command -v node &>/dev/null; then
  fail "node not found — install Node.js 22+: https://nodejs.org/"
  exit 1
fi
ok "node $(node --version)"

if [[ ! -d "$HOME/SecondBrain" ]]; then
  mkdir -p "$HOME/SecondBrain"
  ok "~/SecondBrain created"
else
  ok "~/SecondBrain exists"
fi

# ── 2. Python dependencies ────────────────────────────────────────────────────
step "Installing Python dependencies"
cd "$REPO_ROOT"
uv sync --quiet
ok "Dependencies installed"

# ── 3. Brain initialisation ───────────────────────────────────────────────────
step "Initialising brain (sb-init)"
uv run sb-init --yes
ok "Brain initialised"

# ── 4. Frontend build ─────────────────────────────────────────────────────────
step "Building frontend"
npm ci --prefix "$REPO_ROOT/frontend"
npm run build --prefix "$REPO_ROOT/frontend"
ok "Frontend built"

# ── 5. Native macOS integration ───────────────────────────────────────────────
step "Installing native macOS integration (global CLI + launchd + git hooks)"
uv run sb-install
ok "Native integration installed"

# ── 6. Devcontainer prerequisites ─────────────────────────────────────────────
step "Preparing devcontainer config"
CONFIG_DIR="$HOME/.config/second-brain"
mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_DIR/.env.host" ]; then
  echo "# Add environment variables as needed" > "$CONFIG_DIR/.env.host"
  ok "Created $CONFIG_DIR/.env.host"
else
  ok "$CONFIG_DIR/.env.host exists"
fi

# ── 7. Build search index ─────────────────────────────────────────────────────
if [[ "$SKIP_REINDEX" == "false" ]]; then
  step "Building search index (sb-reindex)"
  sb-reindex
  ok "Index built"
else
  printf "  Skipped (run \033[1msb-reindex\033[0m when ready)\n"
fi

# ── Health check ─────────────────────────────────────────────────────────────
step "Running health check"
sb-health

# ── Chrome Extension ──────────────────────────────────────────────────────────
EXTENSION_DIR="$REPO_ROOT/chrome-extension"
if [ -d "$EXTENSION_DIR" ]; then
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  Chrome Extension"
  echo "  A Chrome extension for web capture is available."
  echo ""
  read -rp "  Install Chrome extension? [y/N] " install_ext
  if [[ "$install_ext" =~ ^[Yy]$ ]]; then
    echo ""
    echo "  Installation steps:"
    echo "  1. Open chrome://extensions in Chrome"
    echo "  2. Enable 'Developer mode' (toggle in top-right)"
    echo "  3. Click 'Load unpacked'"
    echo "  4. Select: $EXTENSION_DIR"
    echo "  5. The 'Second Brain Capture' extension should appear"
    echo ""
    # Open Chrome extensions page (macOS)
    if command -v open &>/dev/null; then
      open "chrome://extensions"
    else
      echo "  Open chrome://extensions manually in Chrome."
    fi
    ok "Chrome extension install instructions shown"
  else
    ok "Chrome extension skipped (run setup.sh again to install later)"
  fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Setup complete!"
echo ""
echo "  GUI:          sb-api & → http://localhost:37491/ui"
echo "  CLI search:   sb-search <query>"
echo "  Capture:      sb-capture"
echo "  Health:       sb-health"
echo ""
echo "  Devcontainer: open this folder in VS Code → 'Reopen in Container'"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
